#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Balkes Skor TFF Standings Builder

PC/local tool for weekly standings:
- tries official TFF weekly tables first;
- if weekly official table is unavailable, fetches all league match details and computes week-by-week tables;
- applies manual point penalties for computed tables;
- writes data/seasons/<season>/standings_by_week.json for the Android app;
- can commit and push generated files after a successful run.

Designed for NixOS + Fish, but only needs Python + bs4/lxml.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    BeautifulSoup = None

try:
    from tff_factory import (
        clean_team,
        clean_text,
        date_in_season,
        decode_bytes,
        is_balkes,
        norm,
        parse_detail,
        read_json,
        season_bounds,
        tff_url,
        write_json,
    )
except Exception as exc:  # pragma: no cover
    print(f"tff_factory import edilemedi: {exc}", file=sys.stderr)
    raise

TFF = "https://www.tff.org/Default.aspx"
DEFAULT_PENALTIES = "data/standings_penalties.json"
BUILDER_VERSION = "standings-builder-v1-pc-nix-fish"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_int(value: Any) -> int | None:
    text = clean_text(value)
    text = text.replace("−", "-").replace("+", "")
    m = re.search(r"-?\d+", text)
    return int(m.group(0)) if m else None


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value)[:160]


def fetch_url(url: str, path: Path, sleep_s: float = 0.8, force: bool = False) -> tuple[bool, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 200 and not force:
        return True, path.read_text(encoding="utf-8", errors="replace")
    last = ""
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 BalkesSkorStandingsBuilder/1.0",
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
            })
            with urllib.request.urlopen(req, timeout=75) as res:
                raw = res.read()
                content_type = res.headers.get("Content-Type", "")
            text = decode_bytes(raw, content_type)
            path.write_text(text, encoding="utf-8")
            if sleep_s:
                time.sleep(sleep_s)
            return True, text
        except Exception as exc:
            last = str(exc)
            time.sleep(max(1.5, sleep_s * attempt))
    path.with_suffix(path.suffix + ".error.txt").write_text(last, encoding="utf-8")
    return False, ""


def soup(raw: str):
    if BeautifulSoup is None:
        return None
    return BeautifulSoup(raw, "lxml" if "lxml" in sys.modules else "html.parser")


def extract_match_ids(raw: str) -> list[str]:
    ids = set(re.findall(r"[?&]macId=(\d+)", raw, flags=re.I))
    return sorted(ids, key=lambda x: int(x))


def build_item_urls(item: dict[str, Any], week: int | None = None) -> list[tuple[str, str]]:
    urls: list[tuple[str, str]] = []
    plan = item.get("tffPlan") or {}
    page_id = str(item.get("targetPageID") or plan.get("pageID") or "").strip()
    group_id = str(item.get("targetGrupID") or plan.get("grupID") or "").strip()
    raw_targets = [u for u in item.get("targetUrls", []) or [] if isinstance(u, str) and u.strip()]

    bases: list[tuple[str, str]] = []
    if page_id:
        params: dict[str, Any] = {"pageID": page_id}
        if group_id:
            params["grupID"] = group_id
        bases.append((f"pageID_{page_id}_group_{group_id or 'none'}", TFF + "?" + urllib.parse.urlencode(params)))
    for u in raw_targets:
        label = "extra_" + hashlib.sha1(u.encode("utf-8")).hexdigest()[:10]
        bases.append((label, u.strip()))

    if week is None:
        return bases

    for label, base in bases:
        parsed = urllib.parse.urlparse(base)
        qs = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        for key in ["hafta", "Hafta", "haftaNo", "haftaID", "week"]:
            wqs = dict(qs)
            wqs[key] = str(week)
            url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(wqs)))
            urls.append((f"{label}_{key}_{week:02d}", url))
    return urls


def maybe_header_map(cells: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    aliases = {
        "rank": ["sira", "sıra", "#"],
        "team": ["takim", "takım", "kulup", "kulüp", "team"],
        "played": ["o", "om", "oyn", "oynanan", "mac", "maç"],
        "won": ["g", "galibiyet"],
        "drawn": ["b", "beraberlik"],
        "lost": ["m", "maglubiyet", "mağlubiyet"],
        "goalsFor": ["a", "atilan", "atılan", "attigi", "attığı", "gf"],
        "goalsAgainst": ["y", "yenilen", "yedigi", "yediği", "ga"],
        "goalDifference": ["av", "averaj", "+/-", "gd"],
        "points": ["p", "puan", "pts"],
    }
    for idx, cell in enumerate(cells):
        n = norm(cell)
        compact = re.sub(r"\s+", "", n)
        for key, names in aliases.items():
            if compact in [norm(x).replace(" ", "") for x in names] and key not in out:
                out[key] = idx
    return out


def parse_team_from_cells(cells: list[str], numeric_indexes: set[int]) -> tuple[int | None, str]:
    for i, c in enumerate(cells):
        if i in numeric_indexes:
            continue
        text = clean_text(c)
        if not text:
            continue
        n = norm(text)
        if n in {"takim", "takım", "kulup", "kulüp", "team"}:
            continue
        if re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]", text):
            # Strip leading rank noise but keep team suffixes.
            text = re.sub(r"^\s*\d+\s*[.)-]?\s*", "", text).strip()
            if len(norm(text)) >= 3:
                return i, clean_team(text)
    return None, ""


def row_from_cells(cells: list[str], header: dict[str, int] | None = None) -> dict[str, Any] | None:
    cells = [clean_text(c) for c in cells if clean_text(c)]
    if len(cells) < 4:
        return None
    numeric: list[tuple[int, int]] = []
    for i, c in enumerate(cells):
        v = parse_int(c)
        if v is not None and re.fullmatch(r"[+−\-]?\d+", c.replace(" ", "")):
            numeric.append((i, v))
    numeric_indexes = {i for i, _ in numeric}

    if header and "team" in header and header["team"] < len(cells):
        team = clean_team(cells[header["team"]])
        if not team or not re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]", team):
            _, team = parse_team_from_cells(cells, numeric_indexes)
        row: dict[str, Any] = {"team": team}
        for key in ["rank", "played", "won", "drawn", "lost", "goalsFor", "goalsAgainst", "goalDifference", "points"]:
            idx = header.get(key)
            if idx is not None and idx < len(cells):
                row[key] = parse_int(cells[idx])
        if team and row.get("played") is not None and row.get("points") is not None:
            return normalize_standing_row(row)

    team_idx, team = parse_team_from_cells(cells, numeric_indexes)
    if not team or team_idx is None:
        return None
    nums_after = [v for i, v in numeric if i > team_idx]
    rank = None
    if numeric and numeric[0][0] < team_idx:
        rank = numeric[0][1]
    if len(nums_after) < 5:
        return None
    # Common table: O G B M A Y AV P. If AV omitted: O G B M A Y P.
    row = {"team": team, "rank": rank}
    row["played"] = nums_after[0]
    row["won"] = nums_after[1] if len(nums_after) > 1 else 0
    row["drawn"] = nums_after[2] if len(nums_after) > 2 else 0
    row["lost"] = nums_after[3] if len(nums_after) > 3 else 0
    row["goalsFor"] = nums_after[4] if len(nums_after) > 4 else 0
    row["goalsAgainst"] = nums_after[5] if len(nums_after) > 5 else 0
    if len(nums_after) >= 8:
        row["goalDifference"] = nums_after[6]
        row["points"] = nums_after[7]
    elif len(nums_after) >= 7:
        row["goalDifference"] = row["goalsFor"] - row["goalsAgainst"]
        row["points"] = nums_after[6]
    else:
        return None
    return normalize_standing_row(row)


def normalize_standing_row(row: dict[str, Any]) -> dict[str, Any] | None:
    team = clean_team(row.get("team", ""))
    if not team:
        return None
    played = int(row.get("played") or 0)
    won = int(row.get("won") or 0)
    drawn = int(row.get("drawn") or 0)
    lost = int(row.get("lost") or 0)
    gf = int(row.get("goalsFor") or 0)
    ga = int(row.get("goalsAgainst") or 0)
    gd = int(row.get("goalDifference") if row.get("goalDifference") is not None else gf - ga)
    points = int(row.get("points") or 0)
    if played == 0 and points == 0 and won == 0 and drawn == 0 and lost == 0:
        return None
    return {
        "rank": int(row.get("rank") or 0),
        "team": team,
        "played": played,
        "won": won,
        "drawn": drawn,
        "lost": lost,
        "goalsFor": gf,
        "goalsAgainst": ga,
        "goalDifference": gd,
        "points": points,
        "rawPoints": int(row.get("rawPoints") if row.get("rawPoints") is not None else points),
        "pointsDeducted": int(row.get("pointsDeducted") or 0),
        "penaltyNote": str(row.get("penaltyNote") or ""),
        "isBalkes": bool(is_balkes(team)),
    }


def parse_official_standings(raw: str) -> list[dict[str, Any]]:
    sp = soup(raw)
    if not sp:
        return []
    candidates: list[list[dict[str, Any]]] = []
    for table in sp.find_all("table"):
        header: dict[str, int] | None = None
        rows: list[dict[str, Any]] = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if not cells:
                continue
            hm = maybe_header_map(cells)
            if len(hm) >= 3:
                header = hm
                continue
            row = row_from_cells(cells, header)
            if row:
                rows.append(row)
        if len(rows) >= 4:
            candidates.append(rows)
    if not candidates:
        return []
    # Prefer tables with Balkes and many rows.
    candidates.sort(key=lambda rows: (any(r.get("isBalkes") for r in rows), len(rows)), reverse=True)
    rows = candidates[0]
    # Ensure rank order when missing.
    for i, r in enumerate(rows, 1):
        if not r.get("rank"):
            r["rank"] = i
    return rows


def standings_signature(rows: list[dict[str, Any]]) -> str:
    compact = [(norm(r.get("team", "")), r.get("played"), r.get("points"), r.get("goalDifference")) for r in rows]
    return hashlib.sha1(json.dumps(compact, sort_keys=True).encode("utf-8")).hexdigest()


def load_penalties(path: Path) -> dict[str, Any]:
    if path.exists():
        return read_json(path, {}) or {}
    obj = {
        "schemaVersion": 1,
        "updatedAt": now(),
        "notes": [
            "Computed standings apply these manual point corrections. Official TFF standings are assumed to already include official corrections.",
            "Use negative points for deductions, positive points for restorations/awards.",
            "Set effectiveWeek to the first week where the correction must appear. Omit or set 1 to apply from the start.",
        ],
        "seasons": {},
        "reviewedSeasons": {},
    }
    write_json(path, obj)
    return obj


def penalties_for_week(penalties: dict[str, Any], season: str, week: int) -> list[dict[str, Any]]:
    out = []
    for p in ((penalties.get("seasons") or {}).get(season) or []):
        try:
            eff = int(p.get("effectiveWeek") or 1)
        except Exception:
            eff = 1
        if week >= eff:
            out.append(p)
    return out


def apply_penalties(rows: list[dict[str, Any]], penalties: dict[str, Any], season: str, week: int) -> None:
    active = penalties_for_week(penalties, season, week)
    if not active:
        return
    for row in rows:
        row["rawPoints"] = int(row.get("points") or 0)
        row["pointsDeducted"] = 0
        row["penaltyNote"] = ""
        for p in active:
            if norm(p.get("team", "")) == norm(row.get("team", "")):
                delta = int(p.get("points") or 0)
                row["points"] = int(row.get("points") or 0) + delta
                row["pointsDeducted"] += delta
                note = clean_text(p.get("note", ""))
                if note:
                    row["penaltyNote"] = (row["penaltyNote"] + "; " + note).strip("; ")


def sort_standings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows.sort(key=lambda r: (
        -int(r.get("points") or 0),
        -int(r.get("goalDifference") or 0),
        -int(r.get("goalsFor") or 0),
        norm(r.get("team", "")),
    ))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
        r["isBalkes"] = bool(is_balkes(r.get("team", "")))
    return rows


@dataclass
class TeamStats:
    team: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goalsFor: int = 0
    goalsAgainst: int = 0

    @property
    def points(self) -> int:
        return self.won * 3 + self.drawn

    @property
    def goalDifference(self) -> int:
        return self.goalsFor - self.goalsAgainst

    def row(self) -> dict[str, Any]:
        return {
            "team": self.team,
            "played": self.played,
            "won": self.won,
            "drawn": self.drawn,
            "lost": self.lost,
            "goalsFor": self.goalsFor,
            "goalsAgainst": self.goalsAgainst,
            "goalDifference": self.goalDifference,
            "points": self.points,
            "rawPoints": self.points,
            "pointsDeducted": 0,
            "penaltyNote": "",
            "isBalkes": bool(is_balkes(self.team)),
        }


def update_stats(stats: dict[str, TeamStats], match: dict[str, Any]) -> None:
    home = clean_team(match.get("homeTeam", ""))
    away = clean_team(match.get("awayTeam", ""))
    score = match.get("score") or {}
    if not home or not away or not score.get("played"):
        return
    h = score.get("home")
    a = score.get("away")
    if h is None or a is None:
        return
    h, a = int(h), int(a)
    sh = stats.setdefault(norm(home), TeamStats(home))
    sa = stats.setdefault(norm(away), TeamStats(away))
    sh.played += 1; sa.played += 1
    sh.goalsFor += h; sh.goalsAgainst += a
    sa.goalsFor += a; sa.goalsAgainst += h
    if h > a:
        sh.won += 1; sa.lost += 1
    elif h < a:
        sa.won += 1; sh.lost += 1
    else:
        sh.drawn += 1; sa.drawn += 1


def detail_is_league_match(detail: dict[str, Any], season: str, seed: dict[str, Any]) -> bool:
    if not detail.get("homeTeam") or not detail.get("awayTeam"):
        return False
    if not detail.get("date") or not date_in_season(detail.get("date"), season, seed):
        return False
    score = detail.get("score") or {}
    if not score.get("played"):
        return False
    match_type = detail.get("matchType") or detail.get("type") or ""
    if match_type and match_type != "league":
        return False
    comp = norm(detail.get("competition", ""))
    if "kupa" in comp or "ziraat" in comp or "play" in comp:
        return False
    return True


def collect_week_match_ids(item: dict[str, Any], season: str, raw_root: Path, sleep_s: float, force: bool, max_week: int) -> dict[str, int]:
    by_id: dict[str, int] = {}
    for week in range(1, max_week + 1):
        found_this_week = set()
        for label, url in build_item_urls(item, week):
            ok, raw = fetch_url(url, raw_root / season / "weekly_pages" / f"{safe_name(label)}.html", sleep_s, force)
            if not ok:
                continue
            for mid in extract_match_ids(raw):
                found_this_week.add(mid)
        for mid in found_this_week:
            by_id.setdefault(mid, week)
        log(f"{season}: hafta {week}/{max_week} fikstür ID={len(found_this_week)} toplamID={len(by_id)}")
    if not by_id:
        for label, url in build_item_urls(item, None):
            ok, raw = fetch_url(url, raw_root / season / "weekly_pages" / f"{safe_name(label)}_base.html", sleep_s, force)
            if not ok:
                continue
            for mid in extract_match_ids(raw):
                by_id.setdefault(mid, 0)
    return by_id


def fetch_full_league_matches(item: dict[str, Any], season: str, seed: dict[str, Any], raw_root: Path, sleep_s: float, force: bool, max_week: int, probe_limit: int) -> list[dict[str, Any]]:
    week_by_id = collect_week_match_ids(item, season, raw_root, sleep_s, force, max_week)
    mids = sorted(week_by_id.keys(), key=lambda x: int(x))
    if probe_limit > 0:
        mids = mids[:probe_limit]
    details: list[dict[str, Any]] = []
    for idx, mid in enumerate(mids, 1):
        url = tff_url(pageID=29, macId=mid)
        ok, raw = fetch_url(url, raw_root / season / "match_details" / f"{mid}.html", sleep_s, force)
        if not ok:
            continue
        try:
            detail = parse_detail(mid, raw, season, url, seed)
        except Exception as exc:
            log(f"{season}: macId={mid} parse hata: {exc}")
            continue
        if not detail_is_league_match(detail, season, seed):
            continue
        detail["standingsWeek"] = int(week_by_id.get(mid) or 0)
        details.append(detail)
        if idx % 50 == 0 or idx == len(mids):
            log(f"{season}: detay {idx}/{len(mids)} ligMaçı={len(details)}")
    # If week is unknown, assign by date order roughly using match batches per round.
    if details and all(int(d.get("standingsWeek") or 0) == 0 for d in details):
        teams = sorted({norm(d["homeTeam"]) for d in details} | {norm(d["awayTeam"]) for d in details})
        per_round = max(1, len(teams) // 2)
        details.sort(key=lambda d: (d.get("date") or "", int(d.get("id") or 0)))
        for i, d in enumerate(details):
            d["standingsWeek"] = min(max_week, i // per_round + 1)
    return details


def compute_weekly_standings(matches: list[dict[str, Any]], season: str, max_week: int, penalties: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    stats: dict[str, TeamStats] = {}
    by_week: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for m in matches:
        week = int(m.get("standingsWeek") or 0)
        if week <= 0:
            continue
        by_week[min(week, max_week)].append(m)
    for week in range(1, max_week + 1):
        for m in sorted(by_week.get(week, []), key=lambda d: (d.get("date") or "", int(d.get("id") or 0))):
            update_stats(stats, m)
        rows = [s.row() for s in stats.values()]
        apply_penalties(rows, penalties, season, week)
        rows = sort_standings(rows)
        snapshots.append({
            "week": week,
            "source": "computed_from_tff_results",
            "generatedAt": now(),
            "builderVersion": BUILDER_VERSION,
            "standings": rows,
            "warnings": ["Sıralama puan, averaj, atılan gol ve takım adına göre hesaplandı; TFF özel ikili averaj kuralları ayrıca doğrulanmalıdır."],
        })
    return snapshots


def try_official_weekly(item: dict[str, Any], season: str, raw_root: Path, sleep_s: float, force: bool, max_week: int) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for week in range(1, max_week + 1):
        best: list[dict[str, Any]] = []
        best_url = ""
        for label, url in build_item_urls(item, week):
            ok, raw = fetch_url(url, raw_root / season / "official_tables" / f"{safe_name(label)}.html", sleep_s, force)
            if not ok:
                continue
            rows = parse_official_standings(raw)
            if rows and (not best or len(rows) > len(best) or any(r.get("isBalkes") for r in rows)):
                best = rows
                best_url = url
        if best:
            for i, row in enumerate(best, 1):
                if not row.get("rank"):
                    row["rank"] = i
                row["isBalkes"] = bool(is_balkes(row.get("team", "")))
            snapshots.append({
                "week": week,
                "source": "official_tff_weekly_table",
                "generatedAt": now(),
                "builderVersion": BUILDER_VERSION,
                "sourceUrl": best_url,
                "standings": best,
                "warnings": [],
            })
        log(f"{season}: resmi hafta {week}/{max_week} tablo={'var' if best else 'yok'}")
    if len(snapshots) < max(2, max_week // 3):
        return []
    unique = {standings_signature(s.get("standings") or []) for s in snapshots}
    if max_week > 3 and len(unique) <= 1:
        log(f"{season}: resmi tablo haftalık değişmiyor; computed fallback kullanılacak")
        return []
    return snapshots


def season_item(seed: dict[str, Any], season: str) -> dict[str, Any] | None:
    for item in seed.get("seasons", []) or []:
        if item.get("season") == season:
            return item
    return None


def selected_seasons(seed: dict[str, Any], start: str, max_seasons: int, explicit: list[str] | None = None) -> list[str]:
    if explicit:
        return explicit
    order = seed.get("runOrder") or [x.get("season") for x in seed.get("seasons", []) if x.get("season")]
    if start not in order:
        return [start]
    idx = order.index(start)
    return order[idx: idx + max_seasons]


def update_season_files(data_root: Path, season: str, snapshots: list[dict[str, Any]]) -> None:
    season_dir = data_root / "seasons" / season
    season_dir.mkdir(parents=True, exist_ok=True)
    write_json(season_dir / "standings_by_week.json", snapshots)
    season_json = read_json(season_dir / "season.json", {}) or {"id": season, "name": season}
    files = season_json.setdefault("files", {})
    files["standingsByWeek"] = f"seasons/{season}/standings_by_week.json"
    if snapshots:
        final = snapshots[-1].get("standings") or []
        balkes = next((r for r in final if r.get("isBalkes")), None)
        if balkes:
            summary = season_json.setdefault("summary", {})
            summary["points"] = int(balkes.get("points") or 0)
            summary["rawPoints"] = int(balkes.get("rawPoints") or balkes.get("points") or 0)
            summary["pointsDeducted"] = int(balkes.get("pointsDeducted") or 0)
            summary["finalRank"] = int(balkes.get("rank") or 0)
            summary["goalsFor"] = int(balkes.get("goalsFor") or summary.get("goalsFor") or 0)
            summary["goalsAgainst"] = int(balkes.get("goalsAgainst") or summary.get("goalsAgainst") or 0)
            summary["goalDifference"] = int(balkes.get("goalDifference") or summary.get("goalDifference") or 0)
    season_json["standingsUpdatedAt"] = now()
    season_json["standingsBuilderVersion"] = BUILDER_VERSION
    write_json(season_dir / "season.json", season_json)


def update_manifest(data_root: Path, seasons: list[str]) -> None:
    manifest_path = data_root / "manifest.json"
    manifest = read_json(manifest_path, {}) or {}
    available = manifest.get("availableSeasons") or []
    by_season = {s.get("id"): s for s in available if isinstance(s, dict)}
    for season in seasons:
        season_json = read_json(data_root / "seasons" / season / "season.json", {}) or {}
        if season in by_season and season_json.get("summary"):
            by_season[season]["summary"] = season_json.get("summary")
            by_season[season]["standingsByWeekUrl"] = f"seasons/{season}/standings_by_week.json"
    manifest["standingsUpdatedAt"] = now()
    manifest["standingsBuilderVersion"] = BUILDER_VERSION
    write_json(manifest_path, manifest)


def commit_and_push(paths: list[str], message: str, push: bool, branch: str) -> None:
    subprocess.run(["git", "add", *paths], check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        log("Commit edilecek değişiklik yok.")
        return
    subprocess.run(["git", "commit", "-m", message], check=True)
    if push:
        subprocess.run(["git", "pull", "--rebase", "origin", branch], check=True)
        subprocess.run(["git", "push", "origin", f"HEAD:{branch}"], check=True)


def process_one(season: str, item: dict[str, Any], args: argparse.Namespace, seed: dict[str, Any], penalties: dict[str, Any]) -> dict[str, Any]:
    data_root = Path(args.data_root)
    raw_root = Path(args.raw_root)
    reports_root = Path(args.reports_root)
    max_week = int(item.get("maxWeek") or (item.get("tffPlan") or {}).get("maxWeek") or args.default_max_week)
    report: dict[str, Any] = {
        "season": season,
        "generatedAt": now(),
        "builderVersion": BUILDER_VERSION,
        "mode": args.mode,
        "maxWeek": max_week,
        "source": "none",
        "weeksGenerated": 0,
        "teams": 0,
        "matchesUsed": 0,
        "penaltiesApplied": len((penalties.get("seasons") or {}).get(season) or []),
        "warnings": [],
    }

    if item.get("skipTff") or item.get("professionalStatus") == "amateur":
        report["source"] = "skipped_amateur_or_no_tff"
        report["warnings"].append(item.get("skipReason") or "Bu sezon TFF profesyonel kayıt taraması için atlandı.")
        write_json(reports_root / f"{season}.json", report)
        log(f"{season}: atlandı ({report['warnings'][-1]})")
        return report

    if not build_item_urls(item, None):
        report["warnings"].append("Registry içinde targetPageID/targetUrls yok; resmi tablo ve full fikstür çekimi yapılamadı.")
        write_json(reports_root / f"{season}.json", report)
        log(f"{season}: hedef TFF URL yok")
        return report

    snapshots: list[dict[str, Any]] = []
    if args.mode in {"auto", "official-only"}:
        log(f"{season}: resmi haftalık tablo deneniyor")
        snapshots = try_official_weekly(item, season, raw_root, args.sleep, args.force, max_week)
        if snapshots:
            report["source"] = "official_tff_weekly_table"
    if not snapshots and args.mode == "official-only":
        report["warnings"].append("Resmi haftalık tablo bulunamadı.")
    if not snapshots and args.mode in {"auto", "computed-only"}:
        log(f"{season}: maç detaylarından hesaplama deneniyor")
        matches = fetch_full_league_matches(item, season, seed, raw_root, args.sleep, args.force, max_week, args.probe_limit)
        report["matchesUsed"] = len(matches)
        teams = sorted({clean_team(m.get("homeTeam", "")) for m in matches} | {clean_team(m.get("awayTeam", "")) for m in matches})
        teams = [t for t in teams if t]
        report["teams"] = len(teams)
        min_matches = max(1, int((len(teams) * max_week / 2) * args.min_match_coverage)) if teams else 1
        if len(matches) >= min_matches or args.allow_partial:
            snapshots = compute_weekly_standings(matches, season, max_week, penalties)
            report["source"] = "computed_from_tff_results"
            if args.allow_partial and len(matches) < min_matches:
                report["warnings"].append(f"Partial tablo yazıldı: {len(matches)} maç, beklenen minimum {min_matches}.")
        else:
            report["warnings"].append(f"Yeterli lig maçı bulunamadı: {len(matches)} maç, minimum eşik {min_matches}. Partial tablo yazılmadı.")
    if snapshots:
        update_season_files(data_root, season, snapshots)
        report["weeksGenerated"] = len(snapshots)
        final = snapshots[-1].get("standings") or []
        report["teams"] = report.get("teams") or len(final)
        report["balkesFinal"] = next((r for r in final if r.get("isBalkes")), None)
    write_json(reports_root / f"{season}.json", report)
    log(f"{season}: tamam source={report['source']} weeks={report['weeksGenerated']} warnings={len(report['warnings'])}")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="sources/tff/registry/balkes_tff_seed_registry.json")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--raw-root", default="sources/tff/standings_raw")
    ap.add_argument("--reports-root", default="reports/standings")
    ap.add_argument("--penalties", default=DEFAULT_PENALTIES)
    ap.add_argument("--start-season", default="2025-2026")
    ap.add_argument("--max-seasons", type=int, default=1)
    ap.add_argument("--season", action="append", help="Specific season. Can be repeated.")
    ap.add_argument("--mode", choices=["auto", "official-only", "computed-only"], default="auto")
    ap.add_argument("--default-max-week", type=int, default=34)
    ap.add_argument("--probe-limit", type=int, default=2500)
    ap.add_argument("--min-match-coverage", type=float, default=0.55)
    ap.add_argument("--allow-partial", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.8)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--branch", default="main")
    args = ap.parse_args()

    seed = read_json(args.seed, {}) or {}
    data_root = Path(args.data_root)
    reports_root = Path(args.reports_root)
    reports_root.mkdir(parents=True, exist_ok=True)
    penalties = load_penalties(Path(args.penalties))
    seasons = selected_seasons(seed, args.start_season, args.max_seasons, args.season)
    log("standings queue=" + ", ".join(seasons))
    reports = []
    changed = []
    for season in seasons:
        item = season_item(seed, season) or {"season": season}
        rep = process_one(season, item, args, seed, penalties)
        reports.append(rep)
        if rep.get("weeksGenerated"):
            changed.append(season)
    if changed:
        update_manifest(data_root, changed)
    summary = {
        "generatedAt": now(),
        "builderVersion": BUILDER_VERSION,
        "seasons": reports,
    }
    write_json(reports_root / "last_run_summary.json", summary)
    if args.commit or args.push:
        paths = [
            str(data_root / "manifest.json"),
            str(data_root / "standings_penalties.json"),
            str(data_root / "seasons"),
            str(reports_root),
        ]
        message = f"Build weekly standings from {seasons[0]} ({len(seasons)} seasons)"
        commit_and_push(paths, message, args.push, args.branch)
    failures = [r for r in reports if not r.get("weeksGenerated") and r.get("source") != "skipped_amateur_or_no_tff"]
    if failures and not args.allow_partial:
        log(f"Uyarı: {len(failures)} sezon için puan tablosu üretilmedi. Raporlara bakın: {args.reports_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

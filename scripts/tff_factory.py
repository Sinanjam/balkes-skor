#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

TFF = "https://www.tff.org/Default.aspx"
FACTORY_VERSION = "v2.1-safe"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def read(path: Path | str, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def write(path: Path | str, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def norm(s: Any) -> str:
    s = str(s or "").lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.translate(str.maketrans({
        "ı": "i", "İ": "i", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u",
        "ş": "s", "Ş": "s", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c"
    }))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def is_balkes(s: Any) -> bool:
    n = norm(s)
    return (
        "balikesirspor" in n
        or "balikesir spor" in n
        or "balikesir" in n
        or "balkes" in n
    )


def tff_url(**params: Any) -> str:
    return TFF + "?" + urllib.parse.urlencode(params)


def text_from_html(raw: str) -> str:
    if BeautifulSoup:
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        raw = soup.get_text("\n")
    else:
        raw = re.sub(r"<[^>]+>", "\n", raw)
    lines = []
    for line in raw.splitlines():
        line = re.sub(r"\s+", " ", html.unescape(line)).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def fetch(url: str, path: Path, sleep_s: float = 1.5, force: bool = False) -> tuple[bool, str]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 200 and not force:
        return True, path.read_text(encoding="utf-8", errors="replace")

    last_error = ""
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 BalkesTFFFactory-v2.1-safe/1.0",
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
            })
            with urllib.request.urlopen(req, timeout=70) as res:
                raw = res.read().decode("utf-8", errors="replace")
            path.write_text(raw, encoding="utf-8")
            time.sleep(sleep_s)
            return True, raw
        except Exception as exc:
            last_error = str(exc)
            log(f"fetch hata {attempt}/3: {url} -> {last_error}")
            time.sleep(max(2.0, sleep_s * attempt))

    path.with_suffix(path.suffix + ".error.txt").write_text(last_error, encoding="utf-8")
    return False, ""


def extract_ids(raw: str, key: str = "macId") -> list[str]:
    return sorted(set(re.findall(rf"(?:[?&]|){re.escape(key)}=(\d+)", raw, re.I)), key=lambda x: int(x))


def extract_param(raw: str, key: str) -> list[str]:
    return sorted(set(re.findall(rf"[?&]{re.escape(key)}=(\d+)", raw, re.I)), key=lambda x: int(x))


def extract_balkes_ids_near_link(raw: str, window: int = 1800) -> list[str]:
    found = []
    for m in re.finditer(r"(?:[?&]|)macId=(\d+)", raw, re.I):
        ctx = raw[max(0, m.start() - window):min(len(raw), m.end() + window)]
        if is_balkes(ctx):
            found.append(m.group(1))
    return sorted(set(found), key=lambda x: int(x))


def parse_score(s: str) -> tuple[int, int, str] | None:
    m = re.search(r"\b(\d{1,2})\s*[-–]\s*(\d{1,2})\b", s)
    if not m:
        return None
    h, a = int(m.group(1)), int(m.group(2))
    return h, a, f"{h}-{a}"


def teams_near_score(txt: str) -> tuple[str, str]:
    lines = [x for x in txt.splitlines() if x.strip()]
    for i, line in enumerate(lines):
        if parse_score(line):
            before = [x for x in lines[max(0, i - 7):i] if len(x) > 2]
            after = [x for x in lines[i + 1:i + 8] if len(x) > 2]
            if before and after:
                return before[-1], after[0]
    return "", ""


def classify_type(*parts: Any) -> tuple[str, str]:
    n = norm(" ".join(str(x or "") for x in parts))
    if any(k in n for k in ["ziraat", "turkiye kupasi", "turkish cup", "ztk", " kupa "]):
        return "cup", "Ziraat Türkiye Kupası"
    if any(k in n for k in ["play off", "playoff", "play offs", "playoffs"]):
        return "playoff", "Play-off"
    if any(k in n for k in ["hazirlik", "friendly"]):
        return "friendly_or_unknown", "Hazırlık/Bilinmeyen"
    return "league", "Lig"


def richness(obj: Any) -> int:
    if not isinstance(obj, dict):
        return 0
    score = len(json.dumps(obj, ensure_ascii=False)) // 160
    if isinstance(obj.get("events"), list):
        score += len(obj["events"]) * 10
    if isinstance(obj.get("lineups"), dict):
        score += len(json.dumps(obj["lineups"], ensure_ascii=False)) // 80
    for key in ["homeTeam", "awayTeam", "date", "time", "competition", "week", "stage"]:
        if obj.get(key):
            score += 6
    if isinstance(obj.get("score"), dict) and obj["score"].get("display"):
        score += 10
    return score


def should_replace(old: Any, new: dict[str, Any]) -> bool:
    # Kritik güvenlik: yeni parse belirgin şekilde daha zengin değilse eski detay korunur.
    return not isinstance(old, dict) or not old or richness(new) >= richness(old) + 25


def parse_detail(mid: str, raw: str, season: str, source_url: str, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    fallback = fallback or {}
    txt = text_from_html(raw)
    sc = parse_score(txt)
    home, away = teams_near_score(txt)

    home = fallback.get("homeTeam") or home
    away = fallback.get("awayTeam") or away

    if sc:
        h, a, display = sc
    else:
        old_score = fallback.get("score") if isinstance(fallback.get("score"), dict) else {}
        h, a, display = old_score.get("home"), old_score.get("away"), old_score.get("display", "")

    is_home = is_balkes(home)
    opponent = away if is_home else home
    gf = h if is_home else a
    ga = a if is_home else h
    result = ""
    try:
        result = "W" if gf > ga else "D" if gf == ga else "L"
    except Exception:
        pass

    mt, ml = classify_type(fallback.get("competition"), fallback.get("roundType"), fallback.get("stage"), txt)

    return {
        "id": str(mid),
        "season": season,
        "homeTeam": home,
        "awayTeam": away,
        "date": fallback.get("date", ""),
        "time": fallback.get("time", ""),
        "dateDisplay": fallback.get("dateDisplay", ""),
        "competition": fallback.get("competition", ""),
        "roundType": fallback.get("roundType", ""),
        "week": fallback.get("week", ""),
        "stage": fallback.get("stage", ""),
        "matchType": fallback.get("matchType") or mt,
        "matchTypeLabel": fallback.get("matchTypeLabel") or ml,
        "score": {"home": h, "away": a, "display": display, "played": bool(display)},
        "balkes": {
            "isHome": is_home,
            "opponent": opponent,
            "goalsFor": gf,
            "goalsAgainst": ga,
            "result": result,
        },
        "events": [],
        "referees": [],
        "lineups": {},
        "rawText": txt[:20000],
        "quality": "B" if home and away and display else "D",
        "source": {
            "name": "TFF",
            "url": source_url,
            "retrievedAt": now(),
            "sourceType": "official_tff_match_detail",
        },
    }


def merge_old_index(index_item: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    # Index'te daha temiz alan varsa koru.
    for key in [
        "competition", "roundType", "week", "stage", "date", "time", "dateDisplay",
        "homeTeam", "awayTeam", "score", "balkes", "matchType", "matchTypeLabel"
    ]:
        if isinstance(index_item, dict) and index_item.get(key) not in (None, "", {}, []):
            detail[key] = index_item[key]
    if not detail.get("matchType"):
        mt, ml = classify_type(detail.get("competition"), detail.get("roundType"), detail.get("stage"), detail.get("rawText"))
        detail["matchType"] = mt
        detail["matchTypeLabel"] = ml
    return detail


def index_from_detail(detail: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "id", "season", "competition", "roundType", "week", "stage", "date", "time",
        "dateDisplay", "homeTeam", "awayTeam", "matchType", "matchTypeLabel", "score", "balkes"
    ]
    out = {k: detail.get(k) for k in keys if detail.get(k) is not None}
    out["detailUrl"] = f"seasons/{detail['season']}/matches/{detail['id']}.json"
    out["source"] = detail["source"]
    return out


def row_team_and_numbers(cells: list[str]) -> tuple[str, list[int]]:
    joined = " ".join(cells)
    nums = [int(x) for x in re.findall(r"\b\d+\b", joined)]

    # En güvenilir yol: Balıkesirspor geçen hücreyi takım adı say.
    for cell in cells:
        if is_balkes(cell):
            return cell, nums

    # TFF tablolarında genelde sıra no + takım adı + sayılar gelir.
    candidates = []
    for cell in cells:
        n = norm(cell)
        if not n or n in {"takim", "takimlar", "o", "g", "b", "m", "a", "y", "av", "p", "puan"}:
            continue
        if re.fullmatch(r"[\d+\-–]+", cell):
            continue
        if len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", cell)) >= 3:
            candidates.append(cell)

    team = candidates[0] if candidates else ""
    return team, nums


def parse_standings(raw: str) -> list[dict[str, Any]]:
    if not BeautifulSoup:
        return []

    soup = BeautifulSoup(raw, "html.parser")
    candidate_tables = []

    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [html.unescape(c.get_text(" ", strip=True)).strip() for c in tr.find_all(["td", "th"])]
            cells = [c for c in cells if c]
            if len(cells) < 3:
                continue

            team, nums = row_team_and_numbers(cells)
            if not team or len(nums) < 3:
                continue

            gf = nums[5] if len(nums) > 5 else 0
            ga = nums[6] if len(nums) > 6 else 0
            rows.append({
                "rank": nums[0] if nums else len(rows) + 1,
                "team": team,
                "played": nums[1] if len(nums) > 1 else 0,
                "won": nums[2] if len(nums) > 2 else 0,
                "drawn": nums[3] if len(nums) > 3 else 0,
                "lost": nums[4] if len(nums) > 4 else 0,
                "goalsFor": gf,
                "goalsAgainst": ga,
                "goalDifference": gf - ga,
                "points": nums[-1],
                "isBalkes": is_balkes(team),
                "_cells": cells,
            })

        clean = []
        seen_teams = set()
        for row in rows:
            key = norm(row["team"])
            if key in seen_teams:
                continue
            seen_teams.add(key)
            row.pop("_cells", None)
            clean.append(row)

        if len(clean) >= 4:
            candidate_tables.append(clean)

    # Balıkesirspor içeren tabloyu tercih et; yoksa en uzun tabloyu döndür.
    with_balkes = [t for t in candidate_tables if any(r.get("isBalkes") for r in t)]
    if with_balkes:
        return max(with_balkes, key=len)
    return max(candidate_tables, key=len) if candidate_tables else []


def old_index(data_root: Path, season: str) -> dict[str, dict[str, Any]]:
    arr = read(data_root / "seasons" / season / "matches_index.json", [])
    if not isinstance(arr, list):
        return {}
    return {str(m["id"]): m for m in arr if isinstance(m, dict) and m.get("id")}


def discover(item: dict[str, Any], raw_root: Path, sleep_s: float) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    season = item["season"]
    selected: set[str] = set()
    all_ids: set[str] = set()
    tables: list[dict[str, Any]] = []

    for page_id in item.get("pageIds", []):
        page_url = tff_url(pageID=page_id)
        ok, raw = fetch(page_url, raw_root / season / "pages" / f"pageID_{page_id}.html", sleep_s)
        if not ok:
            continue

        all_ids.update(extract_ids(raw))
        selected.update(extract_balkes_ids_near_link(raw))

        table = parse_standings(raw)
        if table:
            tables.append({"pageID": page_id, "groupID": None, "week": None, "url": page_url, "standings": table})

        groups = extract_param(raw, "grupID")
        weeks = extract_param(raw, "hafta") + extract_param(raw, "haftaID") + extract_param(raw, "haftaNo")

        for gid in groups[:25]:
            group_url = tff_url(pageID=page_id, grupID=gid)
            ok2, group_raw = fetch(group_url, raw_root / season / "standings" / f"pageID_{page_id}_group_{gid}.html", sleep_s)
            if not ok2:
                continue

            all_ids.update(extract_ids(group_raw))
            selected.update(extract_balkes_ids_near_link(group_raw))

            table = parse_standings(group_raw)
            if table:
                tables.append({"pageID": page_id, "groupID": gid, "week": None, "url": group_url, "standings": table})

            if not item.get("tryWeeklyStandings", True):
                continue

            candidate_weeks = sorted(
                set(weeks + extract_param(group_raw, "hafta") + extract_param(group_raw, "haftaID") + extract_param(group_raw, "haftaNo") + [str(x) for x in range(1, 41)]),
                key=lambda x: int(x),
            )
            seen_hashes: set[str] = set()
            for week in candidate_weeks:
                week_url = tff_url(pageID=page_id, grupID=gid, hafta=week)
                ok3, week_raw = fetch(week_url, raw_root / season / "standings" / f"pageID_{page_id}_group_{gid}_week_{week}.html", sleep_s)
                if not ok3:
                    continue
                table = parse_standings(week_raw)
                if not table:
                    continue
                h = hashlib.sha1(json.dumps(table, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                tables.append({"pageID": page_id, "groupID": gid, "week": int(week), "url": week_url, "standings": table})

    return sorted(selected, key=lambda x: int(x)), sorted(all_ids, key=lambda x: int(x)), tables


def fetch_detail_if_balkes(mid: str, season: str, raw_root: Path, sleep_s: float, force: bool, fallback: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, bool]:
    fallback = fallback or {}
    for source_url in [tff_url(macId=mid, pageID=528), tff_url(pageID=29, macId=mid)]:
        ok, raw = fetch(source_url, raw_root / season / "matches" / f"{mid}.html", sleep_s, force)
        if not ok:
            continue
        txt = text_from_html(raw)
        if is_balkes(txt) or fallback:
            return merge_old_index(fallback, parse_detail(mid, raw, season, source_url, fallback)), True
    return None, False


def probe_detail_ids(all_ids: list[str], known: set[str], season: str, raw_root: Path, sleep_s: float, force: bool, max_probe: int) -> list[str]:
    hits = []
    candidates = [mid for mid in all_ids if mid not in known]
    if max_probe > 0:
        candidates = candidates[:max_probe]

    log(f"{season}: detail fallback probe başladı: candidates={len(candidates)}")
    for i, mid in enumerate(candidates, start=1):
        detail, hit = fetch_detail_if_balkes(mid, season, raw_root, sleep_s, force, {})
        if hit and detail and is_balkes((detail.get("homeTeam", "") + " " + detail.get("awayTeam", "") + " " + detail.get("rawText", ""))):
            hits.append(mid)
        if i % 50 == 0:
            log(f"{season}: detail fallback probe {i}/{len(candidates)}, hits={len(hits)}")

    log(f"{season}: detail fallback probe bitti: hits={len(hits)}")
    return sorted(set(hits), key=lambda x: int(x))


def totals(data_root: Path) -> tuple[int, int]:
    manifest = read(data_root / "manifest.json", {})
    seasons = manifest.get("availableSeasons", []) if isinstance(manifest, dict) else []
    return len(seasons), sum(int(s.get("matchCount") or 0) for s in seasons if isinstance(s, dict))


def merge_manifest(data_root: Path, counts: dict[str, int], min_seasons: int, min_matches: int) -> None:
    path = data_root / "manifest.json"
    manifest = read(path, {})
    if not isinstance(manifest, dict):
        raise RuntimeError("manifest yok/bozuk")

    by_id = {str(s["id"]): dict(s) for s in manifest.get("availableSeasons", []) if isinstance(s, dict) and s.get("id")}
    for season, count in counts.items():
        if count <= 0:
            continue
        item = by_id.get(season, {"id": season, "name": season})
        item["matchCount"] = count
        by_id[season] = item

    manifest["availableSeasons"] = [by_id[k] for k in sorted(by_id, reverse=True)]
    manifest["lastUpdated"] = now()
    manifest["appDataVersion"] = int(manifest.get("appDataVersion") or 9) + 1

    total = sum(int(s.get("matchCount") or 0) for s in manifest["availableSeasons"])
    if len(manifest["availableSeasons"]) < min_seasons or total < min_matches:
        raise RuntimeError(f"publish safety stopped: seasons={len(manifest['availableSeasons'])}, matches={total}")

    write(path, manifest)


def update_report(data_root: Path, min_matches: int) -> None:
    seasons = []
    total = 0
    for p in sorted((data_root / "seasons").glob("*/matches_index.json"), reverse=True):
        arr = read(p, [])
        count = len(arr) if isinstance(arr, list) else 0
        total += count
        seasons.append({"id": p.parent.name, "matchCount": count})

    if total < min_matches:
        raise RuntimeError(f"report safety stopped: total={total}")

    report = read(data_root / "data_report.json", {}) or {}
    report.update({
        "generatedAt": now(),
        "sourcePolicy": "TFF-only",
        "factoryVersion": FACTORY_VERSION,
        "totalAppMatches": total,
        "seasons": seasons,
    })
    notes = report.get("notes") if isinstance(report.get("notes"), list) else []
    note = "Factory v2.1-safe: selectedIds boşsa TFF maç detaylarını tek tek açıp Balıkesirspor geçenleri güvenli fallback ile yakalar."
    if note not in notes:
        notes.append(note)
    report["notes"] = notes
    write(data_root / "data_report.json", report)


def process_season(item: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    season = item["season"]
    data_root = Path(args.data_root)
    raw_root = Path(args.raw_root)
    reports_root = Path(args.reports_root)

    log(f"=== {season} başladı ===")
    old = old_index(data_root, season)
    selected, all_ids, table_candidates = discover(item, raw_root, args.sleep)

    known = set(old) | set(map(str, item.get("knownMatchIds", []))) | set(selected)

    fallback_hits: list[str] = []
    # v2.1: Sayfa bağlamında Balıkesirspor seçilemediyse, detay sayfası doğrulamasıyla ara.
    # Bu özellikle elde hiç maç olmayan eski sezonlar için gerekli.
    if not selected and all_ids:
        fallback_hits = probe_detail_ids(
            all_ids=all_ids,
            known=known,
            season=season,
            raw_root=raw_root,
            sleep_s=args.sleep,
            force=args.force,
            max_probe=args.max_discovery_probe,
        )
        known.update(fallback_hits)

    log(
        f"{season}: selectedIds={len(selected)}, allDiscoveredIds={len(all_ids)}, "
        f"fallbackDetailHits={len(fallback_hits)}, existingIds={len(old)}, "
        f"finalQueue={len(known)}, standingsCandidates={len(table_candidates)}"
    )

    season_dir = data_root / "seasons" / season
    matches_dir = season_dir / "matches"
    matches_dir.mkdir(parents=True, exist_ok=True)

    published: dict[str, dict[str, Any]] = {}
    kept_richer = 0
    replaced = 0
    created = 0

    for mid in sorted(known, key=lambda x: int(x)):
        fallback = old.get(mid, {})
        new_detail, _ = fetch_detail_if_balkes(mid, season, raw_root, args.sleep, args.force, fallback)

        detail_file = matches_dir / f"{mid}.json"
        existing_detail = read(detail_file, {})

        if new_detail and should_replace(existing_detail, new_detail):
            write(detail_file, new_detail)
            published[mid] = index_from_detail(new_detail)
            if existing_detail:
                replaced += 1
            else:
                created += 1
        elif isinstance(existing_detail, dict) and existing_detail:
            kept_richer += 1
            if existing_detail.get("source"):
                published[mid] = index_from_detail(merge_old_index(fallback, existing_detail))
            elif fallback:
                published[mid] = fallback
        elif fallback:
            published[mid] = fallback

    # Eski index'teki hiçbir maç düşmez.
    for mid, match in old.items():
        published.setdefault(mid, match)

    arr = sorted(published.values(), key=lambda m: (str(m.get("date") or ""), int(str(m.get("id") or 0))))
    write(season_dir / "matches_index.json", arr)

    selected_tables = []
    for candidate in table_candidates:
        table = candidate.get("standings") or []
        if any(row.get("isBalkes") for row in table):
            selected_tables.append({
                "week": candidate.get("week") or len(selected_tables) + 1,
                "source": {
                    "name": "TFF",
                    "url": candidate["url"],
                    "retrievedAt": now(),
                    "sourceType": "official_tff_standings",
                },
                "pageID": candidate.get("pageID"),
                "groupID": candidate.get("groupID"),
                "standings": table,
            })

    if selected_tables:
        uniq = {
            hashlib.sha1(json.dumps(x["standings"], ensure_ascii=False, sort_keys=True).encode()).hexdigest(): x
            for x in selected_tables
        }
        write(season_dir / "standings_by_week.json", sorted(uniq.values(), key=lambda x: int(x["week"])))
    elif not (season_dir / "standings_by_week.json").exists():
        write(season_dir / "standings_by_week.json", [])

    type_counts: dict[str, int] = {}
    for match in arr:
        mt = match.get("matchType") or "league"
        type_counts[mt] = type_counts.get(mt, 0) + 1

    season_json = read(season_dir / "season.json", {}) or {}
    season_json.update({
        "id": season,
        "name": season,
        "factoryVersion": FACTORY_VERSION,
        "sourcePolicy": "TFF-only",
        "updatedAt": now(),
        "summary": {"matches": len(arr), "matchTypes": type_counts},
        "files": {
            "matchesIndex": f"seasons/{season}/matches_index.json",
            "standingsByWeek": f"seasons/{season}/standings_by_week.json",
        },
    })
    write(season_dir / "season.json", season_json)

    quality = {
        "season": season,
        "selectedIds": len(selected),
        "allDiscoveredIds": len(all_ids),
        "fallbackDetailCandidates": max(0, min(len([x for x in all_ids if x not in set(old)]), args.max_discovery_probe if args.max_discovery_probe > 0 else len(all_ids))),
        "fallbackDetailHits": len(fallback_hits),
        "existingIds": len(old),
        "finalQueue": len(known),
        "matchesPublished": len(arr),
        "detailFiles": len(list(matches_dir.glob("*.json"))),
        "detailsCreated": created,
        "detailsReplaced": replaced,
        "detailsKeptBecauseExistingWasRicher": kept_richer,
        "standingsSnapshots": len(read(season_dir / "standings_by_week.json", [])),
        "balkesTableFound": bool(selected_tables),
        "matchTypeCounts": type_counts,
        "generatedAt": now(),
    }
    write(reports_root / "seasons" / f"{season}_quality.json", quality)
    return quality


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="sources/tff/registry/balkes_tff_seed_registry.json")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--raw-root", default="sources/tff/raw")
    parser.add_argument("--reports-root", default="reports/tff_factory")
    parser.add_argument("--start-season", default="2025-2026")
    parser.add_argument("--max-seasons", type=int, default=1)
    parser.add_argument("--sleep", type=float, default=1.5)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-discovery-probe", type=int, default=1500)
    args = parser.parse_args()

    seed = read(args.seed, {})
    baseline = seed.get("baseline", {}) if isinstance(seed, dict) else {}
    min_seasons = int(os.environ.get("BALKES_MIN_SEASONS", baseline.get("minSeasons", 12)))
    min_matches = int(os.environ.get("BALKES_MIN_MATCHES", baseline.get("minMatches", 177)))

    before = totals(Path(args.data_root))
    log(f"before={before}, required>={min_seasons}/{min_matches}")

    by_season = {s["season"]: s for s in seed.get("seasons", []) if isinstance(s, dict) and s.get("season")}
    queue = []
    seen = False
    for season in seed.get("runOrder", []):
        if season == args.start_season:
            seen = True
        if seen and season in by_season:
            queue.append(by_season[season])
    queue = queue[:args.max_seasons]

    if not queue:
        raise SystemExit(f"start-season bulunamadı: {args.start_season}")

    log("queue=" + ", ".join(x["season"] for x in queue))

    processed = []
    counts = {}
    for item in queue:
        result = process_season(item, args)
        processed.append(result)
        counts[item["season"]] = result["matchesPublished"]

    merge_manifest(Path(args.data_root), counts, min_seasons, min_matches)
    update_report(Path(args.data_root), min_matches)
    after = totals(Path(args.data_root))

    write(Path(args.reports_root) / "tff_factory_summary.json", {
        "generatedAt": now(),
        "status": "ok",
        "sourcePolicy": "TFF-only",
        "factoryVersion": FACTORY_VERSION,
        "startSeason": args.start_season,
        "processed": processed,
        "before": {"seasons": before[0], "matches": before[1]},
        "after": {"seasons": after[0], "matches": after[1]},
        "safeToPush": True,
        "notes": [
            "v2.1-safe mevcut zengin maç detaylarını daha zayıf parse ile ezmez.",
            "selectedIds boşsa TFF maç detaylarını tek tek açıp Balıkesirspor geçenleri fallback ile yakalar.",
            "Raw HTML artifact olarak saklanır, repo commit edilmez.",
            "Lig/ZTK/Play-off matchType alanıyla sınıflandırılır.",
            "Puan tablosu parser'ı Balıkesirspor geçen tabloyu tercih eder."
        ],
    })
    log(f"DONE safeToPush=True after={after}")


if __name__ == "__main__":
    main()

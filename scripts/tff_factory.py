#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Balkes TFF Factory Final
TFF-only, resumable-ish, safety-first data collector.

This is intentionally conservative:
- It never lowers the existing manifest below the baseline.
- It never accepts non-TFF sources.
- It keeps raw TFF HTML in sources/tff/raw.
- It starts with 2025-2026 and can work backwards in blocks.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

TFF_BASE = "https://www.tff.org/Default.aspx"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json(path: Path, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def norm(s: Any) -> str:
    s = str(s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.translate(str.maketrans({"ı":"i","İ":"i","ğ":"g","Ğ":"g","ü":"u","Ü":"u","ş":"s","Ş":"s","ö":"o","Ö":"o","ç":"c","Ç":"c"}))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def is_balkes_text(text: Any) -> bool:
    n = norm(text)
    return "balikesirspor" in n or "balikesir spor" in n or "balikesir" in n

def make_tff_url(**params: Any) -> str:
    return TFF_BASE + "?" + urllib.parse.urlencode(params)

def text_from_html(raw: str) -> str:
    if BeautifulSoup:
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        out = soup.get_text("\n")
    else:
        out = re.sub(r"<[^>]+>", "\n", raw)
    lines = [re.sub(r"\s+", " ", html.unescape(x)).strip() for x in out.splitlines()]
    return "\n".join(x for x in lines if x)

def fetch_url(url: str, raw_path: Path, sleep_s: float = 1.5, force: bool = False) -> Tuple[bool, str]:
    raw_path = Path(raw_path)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_path.exists() and raw_path.stat().st_size > 200 and not force:
        return True, raw_path.read_text(encoding="utf-8", errors="replace")

    last_error = ""
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 BalkesTFFFactory/2.0",
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=70) as res:
                raw = res.read().decode("utf-8", errors="replace")
            raw_path.write_text(raw, encoding="utf-8")
            time.sleep(sleep_s)
            return True, raw
        except Exception as ex:
            last_error = str(ex)
            log(f"fetch hata {attempt}/3: {url} -> {last_error}")
            time.sleep(max(2, sleep_s * attempt))
    raw_path.with_suffix(raw_path.suffix + ".error.txt").write_text(last_error, encoding="utf-8")
    return False, ""

def extract_match_ids(raw: str) -> List[str]:
    ids = set()
    for m in re.finditer(r"(?:[?&]|)macId=(\d+)", raw, flags=re.I):
        ids.add(m.group(1))
    return sorted(ids, key=lambda x: int(x))

def extract_param_ids(raw: str, key: str) -> List[str]:
    return sorted(set(re.findall(rf"[?&]{re.escape(key)}=(\d+)", raw, flags=re.I)), key=lambda x: int(x))

def parse_score(s: str):
    m = re.search(r"\b(\d{1,2})\s*[-–]\s*(\d{1,2})\b", s)
    if not m:
        return None
    h, a = int(m.group(1)), int(m.group(2))
    return h, a, f"{h}-{a}"

def teams_near_score(txt: str):
    lines = [x for x in txt.splitlines() if x.strip()]
    for i, line in enumerate(lines):
        if parse_score(line):
            before = [x for x in lines[max(0, i-6):i] if len(x) > 2]
            after = [x for x in lines[i+1:i+7] if len(x) > 2]
            if before and after:
                return before[-1], after[0]
    return "", ""

def parse_match_detail(match_id: str, raw: str, season: str, source_url: str, fallback: Dict[str, Any] | None = None) -> Dict[str, Any]:
    fallback = fallback or {}
    txt = text_from_html(raw)
    sc = parse_score(txt)
    home, away = teams_near_score(txt)
    home = fallback.get("homeTeam") or home
    away = fallback.get("awayTeam") or away

    if sc:
        sh, sa, disp = sc
    else:
        old_score = fallback.get("score") if isinstance(fallback.get("score"), dict) else {}
        sh, sa, disp = old_score.get("home"), old_score.get("away"), old_score.get("display", "")

    is_home = is_balkes_text(home)
    opponent = away if is_home else home
    gf = sh if is_home else sa
    ga = sa if is_home else sh
    result = ""
    try:
        result = "W" if gf > ga else "D" if gf == ga else "L"
    except Exception:
        pass

    d = {
        "id": str(match_id),
        "season": season,
        "homeTeam": home,
        "awayTeam": away,
        "date": fallback.get("date", ""),
        "time": fallback.get("time", ""),
        "dateDisplay": fallback.get("dateDisplay", ""),
        "score": {"home": sh, "away": sa, "display": disp, "played": bool(disp)},
        "balkes": {"isHome": is_home, "opponent": opponent, "goalsFor": gf, "goalsAgainst": ga, "result": result},
        "events": [],
        "referees": [],
        "lineups": {},
        "rawText": txt[:20000],
        "quality": "B" if home and away and disp else "D",
        "source": {"name": "TFF", "url": source_url, "retrievedAt": utc_now(), "sourceType": "official_tff_match_detail"},
    }
    for key in ["competition", "roundType", "week", "stage"]:
        if key in fallback:
            d[key] = fallback[key]
    return d

def index_from_detail(d: Dict[str, Any]) -> Dict[str, Any]:
    keys = ["id", "season", "competition", "roundType", "week", "stage", "date", "time", "dateDisplay", "homeTeam", "awayTeam", "score", "balkes"]
    out = {k: d.get(k) for k in keys if d.get(k) is not None}
    out["detailUrl"] = f"seasons/{d['season']}/matches/{d['id']}.json"
    out["source"] = d["source"]
    return out

def parse_standings(raw: str) -> List[Dict[str, Any]]:
    if not BeautifulSoup:
        return []
    soup = BeautifulSoup(raw, "html.parser")
    best_rows = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            cells = [html.unescape(c).strip() for c in cells if c.strip()]
            if len(cells) < 4:
                continue
            nums = re.findall(r"\b\d+\b", " ".join(cells))
            if len(nums) >= 3:
                rows.append(cells)
        if len(rows) > len(best_rows):
            best_rows = rows

    parsed = []
    for i, cells in enumerate(best_rows, start=1):
        team = next((c for c in cells if not re.fullmatch(r"[\d+\-–]+", c) and len(c) > 2 and "takim" not in norm(c)), "")
        nums = [int(x) for x in re.findall(r"\b\d+\b", " ".join(cells))]
        if not team or len(nums) < 3:
            continue
        gf = nums[5] if len(nums) > 5 else 0
        ga = nums[6] if len(nums) > 6 else 0
        parsed.append({
            "rank": nums[0] if nums else i,
            "team": team,
            "played": nums[1] if len(nums) > 1 else 0,
            "won": nums[2] if len(nums) > 2 else 0,
            "drawn": nums[3] if len(nums) > 3 else 0,
            "lost": nums[4] if len(nums) > 4 else 0,
            "goalsFor": gf,
            "goalsAgainst": ga,
            "goalDifference": gf - ga,
            "points": nums[-1],
            "isBalkes": is_balkes_text(team),
        })
    return parsed if len(parsed) >= 4 else []

def existing_index(data_root: Path, season: str) -> Dict[str, Dict[str, Any]]:
    arr = read_json(data_root / "seasons" / season / "matches_index.json", [])
    return {str(m["id"]): m for m in arr if isinstance(m, dict) and m.get("id")} if isinstance(arr, list) else {}

def manifest_totals(data_root: Path):
    m = read_json(data_root / "manifest.json", {})
    seasons = m.get("availableSeasons", []) if isinstance(m, dict) else []
    return len(seasons), sum(int(s.get("matchCount") or 0) for s in seasons if isinstance(s, dict))

def discover_from_pages(item: Dict[str, Any], raw_root: Path, sleep: float):
    season = item["season"]
    match_ids = set()
    standings_candidates = []

    for page_id in item.get("pageIds", []):
        page_url = make_tff_url(pageID=page_id)
        ok, raw = fetch_url(page_url, raw_root / season / "pages" / f"pageID_{page_id}.html", sleep)
        if not ok:
            continue
        match_ids.update(extract_match_ids(raw))

        group_ids = extract_param_ids(raw, "grupID")
        week_links = extract_param_ids(raw, "hafta") + extract_param_ids(raw, "haftaID") + extract_param_ids(raw, "haftaNo")

        table = parse_standings(raw)
        if table:
            standings_candidates.append({"pageID": page_id, "groupID": None, "week": None, "url": page_url, "standings": table})

        for gid in group_ids[:25]:
            group_url = make_tff_url(pageID=page_id, grupID=gid)
            ok2, group_raw = fetch_url(group_url, raw_root / season / "standings" / f"pageID_{page_id}_group_{gid}.html", sleep)
            if not ok2:
                continue
            match_ids.update(extract_match_ids(group_raw))
            table = parse_standings(group_raw)
            if table:
                standings_candidates.append({"pageID": page_id, "groupID": gid, "week": None, "url": group_url, "standings": table})

            if item.get("tryWeeklyStandings", True):
                weeks = sorted(set(week_links + extract_param_ids(group_raw, "hafta") + extract_param_ids(group_raw, "haftaID") + extract_param_ids(group_raw, "haftaNo") + [str(x) for x in range(1, 41)]), key=lambda x: int(x))
                seen = set()
                for week in weeks:
                    week_url = make_tff_url(pageID=page_id, grupID=gid, hafta=week)
                    ok3, week_raw = fetch_url(week_url, raw_root / season / "standings" / f"pageID_{page_id}_group_{gid}_week_{week}.html", sleep)
                    if not ok3:
                        continue
                    table = parse_standings(week_raw)
                    if table:
                        h = hashlib.sha1(json.dumps(table, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                        if h not in seen:
                            seen.add(h)
                            standings_candidates.append({"pageID": page_id, "groupID": gid, "week": int(week), "url": week_url, "standings": table})

    return sorted(match_ids, key=lambda x: int(x)), standings_candidates

def merge_manifest(data_root: Path, season_counts: Dict[str, int], min_seasons: int, min_matches: int):
    path = data_root / "manifest.json"
    manifest = read_json(path, {})
    if not isinstance(manifest, dict):
        manifest = {"app": "Balkes Skor", "team": "Balıkesirspor", "schemaVersion": 2}

    by_id = {}
    for s in manifest.get("availableSeasons", []):
        if isinstance(s, dict) and s.get("id"):
            by_id[str(s["id"])] = dict(s)

    for sid, count in season_counts.items():
        if count <= 0:
            continue
        item = by_id.get(sid, {"id": sid, "name": sid})
        item["matchCount"] = count
        by_id[sid] = item

    manifest["availableSeasons"] = [by_id[x] for x in sorted(by_id, reverse=True)]
    manifest["app"] = "Balkes Skor"
    manifest["team"] = "Balıkesirspor"
    manifest["schemaVersion"] = int(manifest.get("schemaVersion") or 2)
    manifest["appDataVersion"] = int(manifest.get("appDataVersion") or 9) + 1
    manifest["lastUpdated"] = utc_now()
    manifest.setdefault("global", {
        "playersIndexUrl": "players_index.json",
        "opponentsIndexUrl": "opponents_index.json",
        "searchIndexUrl": "search_index.json",
        "dataReportUrl": "data_report.json"
    })

    season_total = len(manifest["availableSeasons"])
    match_total = sum(int(s.get("matchCount") or 0) for s in manifest["availableSeasons"])
    if season_total < min_seasons or match_total < min_matches:
        raise RuntimeError(f"publish safety stopped: seasons={season_total}, matches={match_total}")

    write_json(path, manifest)

def update_report(data_root: Path, min_matches: int):
    seasons = []
    total = 0
    for p in sorted((data_root / "seasons").glob("*/matches_index.json"), reverse=True):
        arr = read_json(p, [])
        cnt = len(arr) if isinstance(arr, list) else 0
        total += cnt
        sj = read_json(p.parent / "season.json", {})
        seasons.append({"id": p.parent.name, "matchCount": cnt, "competition": sj.get("competition", "") if isinstance(sj, dict) else ""})

    if total < min_matches:
        raise RuntimeError(f"report safety stopped: total={total}")

    report = read_json(data_root / "data_report.json", {})
    if not isinstance(report, dict):
        report = {}
    report.update({
        "generatedAt": utc_now(),
        "sourcePolicy": "TFF-only",
        "sourceZip": "Balkes TFF Factory Final",
        "totalAppMatches": total,
        "seasons": seasons,
    })
    notes = report.get("notes") if isinstance(report.get("notes"), list) else []
    note = "Balkes TFF Factory Final yalnızca resmi/açık TFF sayfalarından veri alacak şekilde çalıştırıldı."
    if note not in notes:
        notes.append(note)
    report["notes"] = notes
    write_json(data_root / "data_report.json", report)

def process_season(item: Dict[str, Any], args, seed):
    season = item["season"]
    data_root = Path(args.data_root)
    raw_root = Path(args.raw_root)
    reports_root = Path(args.reports_root)
    log(f"=== {season} başladı ===")

    old = existing_index(data_root, season)
    known = {str(x) for x in item.get("knownMatchIds", [])} | set(old.keys())

    discovered, standing_candidates = discover_from_pages(item, raw_root, args.sleep)
    known |= set(discovered)
    log(f"{season}: known={len(known)}, discovered={len(discovered)}, standingsCandidates={len(standing_candidates)}")

    season_dir = data_root / "seasons" / season
    matches_dir = season_dir / "matches"
    matches_dir.mkdir(parents=True, exist_ok=True)

    published = {}
    for n, mid in enumerate(sorted(known, key=lambda x: int(x)), start=1):
        if args.max_matches and n > args.max_matches:
            break

        fallback = old.get(mid, {})
        detail = None
        for candidate_url in [make_tff_url(macId=mid, pageID=528), make_tff_url(pageID=29, macId=mid)]:
            ok, raw = fetch_url(candidate_url, raw_root / season / "matches" / f"{mid}.html", args.sleep, args.force)
            if ok and (is_balkes_text(text_from_html(raw)) or fallback):
                detail = parse_match_detail(mid, raw, season, candidate_url, fallback)
                break

        if detail:
            # Keep existing index data when it is stronger than generic parser.
            for key in ["competition", "roundType", "week", "stage", "date", "time", "dateDisplay", "homeTeam", "awayTeam", "score", "balkes"]:
                if fallback.get(key) not in (None, "", {}, []):
                    detail[key] = fallback[key]
            write_json(matches_dir / f"{mid}.json", detail)
            published[mid] = index_from_detail(detail)

    # Data-loss guard: never remove old matches from index.
    for mid, existing in old.items():
        published.setdefault(mid, existing)

    arr = sorted(published.values(), key=lambda m: (str(m.get("date") or ""), int(str(m.get("id") or 0))))
    write_json(season_dir / "matches_index.json", arr)

    selected_standings = []
    for candidate in standing_candidates:
        table = candidate.get("standings") or []
        if any(r.get("isBalkes") for r in table):
            selected_standings.append({
                "week": candidate.get("week") or len(selected_standings) + 1,
                "source": {"name": "TFF", "url": candidate["url"], "retrievedAt": utc_now(), "sourceType": "official_tff_standings"},
                "pageID": candidate.get("pageID"),
                "groupID": candidate.get("groupID"),
                "standings": table
            })

    if selected_standings:
        uniq = {}
        for item2 in selected_standings:
            h = hashlib.sha1(json.dumps(item2["standings"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            uniq[h] = item2
        write_json(season_dir / "standings_by_week.json", sorted(uniq.values(), key=lambda x: int(x["week"])))
    elif not (season_dir / "standings_by_week.json").exists():
        write_json(season_dir / "standings_by_week.json", [])

    summary = {
        "matches": len(arr),
        "wins": sum((m.get("balkes") or {}).get("result") == "W" for m in arr),
        "draws": sum((m.get("balkes") or {}).get("result") == "D" for m in arr),
        "losses": sum((m.get("balkes") or {}).get("result") == "L" for m in arr),
        "goalsFor": sum(int((m.get("balkes") or {}).get("goalsFor") or 0) for m in arr),
        "goalsAgainst": sum(int((m.get("balkes") or {}).get("goalsAgainst") or 0) for m in arr),
    }
    summary["goalDifference"] = summary["goalsFor"] - summary["goalsAgainst"]

    season_json = read_json(season_dir / "season.json", {})
    if not isinstance(season_json, dict):
        season_json = {}
    season_json.update({
        "id": season,
        "name": season,
        "competition": season_json.get("competition") or item.get("competitionGuess", ""),
        "summary": summary,
        "files": {
            "matchesIndex": f"seasons/{season}/matches_index.json",
            "standingsByWeek": f"seasons/{season}/standings_by_week.json"
        },
        "sourcePolicy": "TFF-only",
        "updatedAt": utc_now(),
    })
    write_json(season_dir / "season.json", season_json)

    quality = {
        "season": season,
        "knownIds": len(known),
        "discoveredIds": len(discovered),
        "matchesPublished": len(arr),
        "detailFiles": len(list(matches_dir.glob("*.json"))),
        "standingsSnapshots": len(read_json(season_dir / "standings_by_week.json", [])),
        "balkesTableFound": bool(selected_standings),
        "generatedAt": utc_now()
    }
    write_json(reports_root / "seasons" / f"{season}_quality.json", quality)
    return quality

def sync_web_data(app_data: Path, web_data: Path):
    if not web_data:
        return
    web_data = Path(web_data)
    if not web_data.parent.exists():
        log(f"web sync skipped, parent missing: {web_data.parent}")
        return
    if web_data.exists():
        shutil.rmtree(web_data)
    shutil.copytree(app_data, web_data)
    manifest = read_json(web_data / "manifest.json", {})
    if isinstance(manifest, dict):
        manifest["dataBaseUrl"] = "https://raw.githubusercontent.com/Sinanjam/balkes-skor-web/main/docs/data/"
        write_json(web_data / "manifest.json", manifest)
    log(f"web data synced: {web_data}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="sources/tff/registry/balkes_tff_seed_registry.json")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--raw-root", default="sources/tff/raw")
    ap.add_argument("--reports-root", default="reports/tff_factory")
    ap.add_argument("--web-data-root", default="")
    ap.add_argument("--start-season", default="2025-2026")
    ap.add_argument("--max-seasons", type=int, default=1)
    ap.add_argument("--max-matches", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    seed = read_json(Path(args.seed), {})
    if not isinstance(seed, dict):
        raise SystemExit("Seed registry invalid/missing.")

    baseline = seed.get("baseline", {})
    min_seasons = int(os.environ.get("BALKES_MIN_SEASONS", baseline.get("minSeasons", 12)))
    min_matches = int(os.environ.get("BALKES_MIN_MATCHES", baseline.get("minMatches", 177)))

    data_root = Path(args.data_root)
    before = manifest_totals(data_root)
    log(f"before={before}, required>={min_seasons}/{min_matches}")

    by_id = {s["season"]: s for s in seed.get("seasons", []) if isinstance(s, dict) and s.get("season")}
    queue = []
    seen = False
    for sid in seed.get("runOrder", []):
        if sid == args.start_season:
            seen = True
        if seen and sid in by_id:
            queue.append(by_id[sid])
    queue = queue[:args.max_seasons]
    log("queue=" + ", ".join(x["season"] for x in queue))

    processed = []
    season_counts = {}
    for item in queue:
        q = process_season(item, args, seed)
        processed.append(q)
        season_counts[item["season"]] = q["matchesPublished"]

    merge_manifest(data_root, season_counts, min_seasons, min_matches)
    update_report(data_root, min_matches)

    if args.web_data_root:
        sync_web_data(data_root, Path(args.web_data_root))

    after = manifest_totals(data_root)
    if after[0] < min_seasons or after[1] < min_matches:
        raise RuntimeError(f"final safety stopped: after={after}")

    summary = {
        "generatedAt": utc_now(),
        "status": "ok",
        "sourcePolicy": "TFF-only",
        "startSeason": args.start_season,
        "processed": processed,
        "before": {"seasons": before[0], "matches": before[1]},
        "after": {"seasons": after[0], "matches": after[1]},
        "safeToPush": True,
    }
    write_json(Path(args.reports_root) / "tff_factory_summary.json", summary)
    log(f"DONE safeToPush=True after={after}")

if __name__ == "__main__":
    main()

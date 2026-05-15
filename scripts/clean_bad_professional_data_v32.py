#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clean already-published Balkes data from youth/academy/BAL contamination.

Use after a factory run and before committing. It removes non-senior matches,
suppresses empty/partial seasons, and rebuilds manifest/opponents/search/report.
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from tff_factory import norm, is_balkes, write_json, read_json, clean_team  # noqa: E402

FACTORY_VERSION = "v3.2-senior-professional-guard-cleaner"

BANNED = (
    "u21", "u 21", "paf", "akademi", "gelisim", "gelişim", "elit u", "u19", "u 19",
    "u18", "u 18", "u17", "u 17", "u16", "u 16", "u15", "u 15", "u14", "u 14",
    "bolgesel amator", "bölgesel amatör", "bal takimi", "bal takımı", "rezerv", "kadin", "kadın", "futsal",
)
SIGNALS = (
    "profesyonel takim", "super lig", "spor toto super lig", "1 lig", "1lig", "2 lig", "2lig",
    "3 lig", "3lig", "turkiye kupasi", "play off musabakalari",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def is_senior_professional_competition(value: Any) -> bool:
    n = norm(value)
    if not n:
        return False
    if any(norm(x) in n for x in BANNED):
        return False
    if "profesyonel takim" in n:
        return True
    if "turkiye kupasi" in n:
        return True
    if "play off" in n and "lig" in n:
        return True
    return any(x in n for x in SIGNALS)


def match_type(m: dict[str, Any]) -> str:
    return str(m.get("matchType") or m.get("type") or "league")


def score_parts(m: dict[str, Any]) -> tuple[int | None, int | None, bool]:
    s = m.get("score") or {}
    h = s.get("home")
    a = s.get("away")
    try:
        h = int(h) if h is not None else None
        a = int(a) if a is not None else None
    except Exception:
        h = a = None
    return h, a, bool(s.get("played") and h is not None and a is not None)


def valid_match(m: dict[str, Any]) -> tuple[bool, str]:
    comp = m.get("competition") or ""
    if not is_senior_professional_competition(comp):
        return False, "non_senior_competition:" + str(comp)[:100]
    if not (is_balkes(m.get("homeTeam")) or is_balkes(m.get("awayTeam"))):
        return False, "balkes_not_found"
    if not m.get("date"):
        return False, "date_missing"
    return True, "ok"


def update_balkes_fields(m: dict[str, Any]) -> dict[str, Any]:
    home = clean_team(m.get("homeTeam", ""))
    away = clean_team(m.get("awayTeam", ""))
    h, a, played = score_parts(m)
    is_home = is_balkes(home)
    is_away = is_balkes(away)
    gf = h if is_home else a if is_away else None
    ga = a if is_home else h if is_away else None
    result = ""
    if played and gf is not None and ga is not None:
        result = "W" if gf > ga else "D" if gf == ga else "L"
    m["homeTeam"] = home
    m["awayTeam"] = away
    m["balkes"] = {
        "isHome": bool(is_home),
        "isAway": bool(is_away),
        "opponent": away if is_home else home if is_away else "",
        "goalsFor": gf,
        "goalsAgainst": ga,
        "result": result,
    }
    return m


def season_summary(matches: list[dict[str, Any]]) -> dict[str, Any]:
    wins = draws = losses = gf = ga = 0
    type_counts: dict[str, int] = {}
    for m in matches:
        mt = match_type(m)
        type_counts[mt] = type_counts.get(mt, 0) + 1
        b = m.get("balkes") or {}
        if b.get("result") == "W": wins += 1
        elif b.get("result") == "D": draws += 1
        elif b.get("result") == "L": losses += 1
        if b.get("goalsFor") is not None: gf += int(b.get("goalsFor") or 0)
        if b.get("goalsAgainst") is not None: ga += int(b.get("goalsAgainst") or 0)
    return {"matches": len(matches), "wins": wins, "draws": draws, "losses": losses, "goalsFor": gf, "goalsAgainst": ga, "goalDifference": gf - ga, "matchTypes": type_counts}


def should_suppress(matches: list[dict[str, Any]], min_matches: int, min_league: int, max_matches: int) -> tuple[bool, list[str]]:
    reasons = []
    total = len(matches)
    league = sum(1 for m in matches if match_type(m) == "league")
    if total == 0: reasons.append("empty_after_clean")
    if total < min_matches: reasons.append(f"too_few_matches:{total}")
    if league < min_league: reasons.append(f"too_few_league_matches:{league}")
    if total > max_matches: reasons.append(f"too_many_matches:{total}")
    return bool(reasons), reasons


def process_season_dir(season_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    season = season_dir.name
    index_path = season_dir / "matches_index.json"
    index = read_json(index_path, []) if index_path.exists() else []
    if not isinstance(index, list):
        index = []
    kept: list[dict[str, Any]] = []
    rejected = Counter()
    for item in index:
        if not isinstance(item, dict):
            rejected["bad_index_item"] += 1
            continue
        detail = item
        detail_path = None
        detail_url = str(item.get("detailUrl") or "")
        if detail_url:
            candidate = args.data_root / detail_url
            if candidate.exists():
                loaded = read_json(candidate, None)
                if isinstance(loaded, dict):
                    detail = loaded
                    detail_path = candidate
        ok, reason = valid_match(detail)
        if not ok:
            rejected[reason] += 1
            if detail_path and args.write:
                try: detail_path.unlink()
                except FileNotFoundError: pass
            continue
        detail = update_balkes_fields(detail)
        kept.append(detail)

    # Drop exact duplicates by date/home/away/score/type/competition.
    seen = set()
    deduped = []
    for m in sorted(kept, key=lambda x: (x.get("date") or "", int(str(x.get("id") or 0)))):
        s = m.get("score") or {}
        sig = (m.get("date"), norm(m.get("homeTeam")), norm(m.get("awayTeam")), s.get("display"), match_type(m), norm(m.get("competition")))
        if sig in seen:
            rejected["duplicate_signature"] += 1
            continue
        seen.add(sig)
        deduped.append(m)
    kept = deduped

    suppress, reasons = should_suppress(kept, args.min_matches, args.min_league_matches, args.max_matches)
    report: dict[str, Any] = {
        "season": season,
        "before": len(index),
        "after": len(kept),
        "leagueAfter": sum(1 for m in kept if match_type(m) == "league"),
        "rejected": dict(rejected),
        "suppressed": suppress,
        "suppressionReasons": reasons,
        "competitionsAfter": dict(Counter(str(m.get("competition") or "") for m in kept)),
    }
    if suppress:
        if args.write and season_dir.exists():
            shutil.rmtree(season_dir)
        return report

    if args.write:
        matches_dir = season_dir / "matches"
        matches_dir.mkdir(parents=True, exist_ok=True)
        new_index = []
        for m in kept:
            mid = str(m.get("id"))
            m["season"] = season
            m.setdefault("detailUrl", f"seasons/{season}/matches/{mid}.json")
            write_json(matches_dir / f"{mid}.json", m)
            # Keep compact index fields used by the app.
            new_index.append({k: m.get(k) for k in ["id", "matchCode", "season", "competition", "competitionType", "competitionLabel", "stadium", "venue", "stage", "stageLabel", "date", "time", "dateDisplay", "homeTeam", "awayTeam", "matchType", "matchTypeLabel", "type", "typeLabel", "score", "balkes", "quality", "detailCompleteness", "source", "detailUrl"] if k in m})
        write_json(index_path, new_index)
        season_json = read_json(season_dir / "season.json", {}) or {}
        if not isinstance(season_json, dict): season_json = {}
        season_json.update({
            "id": season,
            "name": season,
            "competition": kept[0].get("competition", "") if kept else season_json.get("competition", ""),
            "sourcePolicy": "TFF senior professional only",
            "factoryVersion": FACTORY_VERSION,
            "updatedAt": now(),
            "summary": season_summary(new_index),
            "files": {"matchesIndex": f"seasons/{season}/matches_index.json", "standingsByWeek": f"seasons/{season}/standings_by_week.json"},
        })
        write_json(season_dir / "season.json", season_json)
        if not (season_dir / "standings_by_week.json").exists():
            write_json(season_dir / "standings_by_week.json", [])
    return report


def rebuild_global(data_root: Path, reports_root: Path, reports: list[dict[str, Any]]) -> None:
    seasons = []
    opponents: dict[str, dict[str, Any]] = {}
    search = []
    for p in sorted((data_root / "seasons").glob("*/matches_index.json"), reverse=True):
        arr = read_json(p, [])
        if not isinstance(arr, list) or not arr:
            continue
        season_json = read_json(p.parent / "season.json", {}) or {}
        item = {"id": p.parent.name, "name": p.parent.name, "matchCount": len(arr)}
        if season_json.get("competition"): item["competition"] = season_json.get("competition")
        if season_json.get("summary"): item["summary"] = season_json.get("summary")
        if (p.parent / "standings_by_week.json").exists(): item["standingsByWeekUrl"] = f"seasons/{p.parent.name}/standings_by_week.json"
        seasons.append(item)
        for m in arr:
            b = m.get("balkes") or {}
            opp = b.get("opponent")
            if opp:
                x = opponents.setdefault(norm(opp), {"name": opp, "matches": 0})
                x["matches"] += 1
            search.append({"type": "match", "season": m.get("season"), "id": m.get("id"), "title": f"{m.get('homeTeam','')} {(m.get('score') or {}).get('display','')} {m.get('awayTeam','')}", "date": m.get("date"), "url": m.get("detailUrl")})
    write_json(data_root / "manifest.json", {
        "app": "Balkes Skor",
        "schemaVersion": 3,
        "dataVersion": 1,
        "generatedAt": now(),
        "team": "Balıkesirspor",
        "availableSeasons": seasons,
        "global": {"playersIndexUrl": "players_index.json", "opponentsIndexUrl": "opponents_index.json", "searchIndexUrl": "search_index.json", "dataReportUrl": "data_report.json"},
        "dataBaseUrl": "https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/",
        "factoryVersion": FACTORY_VERSION,
        "seniorProfessionalGuard": True,
    })
    write_json(data_root / "players_index.json", [])
    write_json(data_root / "opponents_index.json", sorted(opponents.values(), key=lambda x: norm(x["name"])))
    write_json(data_root / "search_index.json", search)
    write_json(data_root / "data_report.json", {
        "generatedAt": now(),
        "sourcePolicy": "TFF senior professional only",
        "factoryVersion": FACTORY_VERSION,
        "totalAppMatches": sum(int(s.get("matchCount") or 0) for s in seasons),
        "seasons": seasons,
        "playersIndexed": 0,
        "opponentsIndexed": len(opponents),
        "notes": ["v3.2: youth/PAF/academy/BAL contamination removed.", "Seasons with too few senior league matches are suppressed instead of publishing partial data."],
    })
    reports_root.mkdir(parents=True, exist_ok=True)
    write_json(reports_root / "professional_guard_v32_summary.json", {"generatedAt": now(), "reports": reports})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data", type=Path)
    ap.add_argument("--reports-root", default="reports/tff_factory", type=Path)
    ap.add_argument("--min-matches", type=int, default=8)
    ap.add_argument("--min-league-matches", type=int, default=8)
    ap.add_argument("--max-matches", type=int, default=80)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    seasons_root = args.data_root / "seasons"
    reports = []
    if seasons_root.exists():
        for season_dir in sorted(seasons_root.iterdir(), reverse=True):
            if season_dir.is_dir():
                reports.append(process_season_dir(season_dir, args))
    if args.write:
        rebuild_global(args.data_root, args.reports_root, reports)
    print(json.dumps({"write": args.write, "reports": reports}, ensure_ascii=False, indent=2))
    bad = [r for r in reports if r.get("suppressed")]
    print(f"v3.2 professional guard: seasons={len(reports)} suppressed={len(bad)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

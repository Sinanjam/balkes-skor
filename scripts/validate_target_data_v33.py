#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Balkes Skor target data after v3.3 cleaning/building."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import sys
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from tff_factory import norm, is_balkes, read_json, write_json  # noqa: E402

BANNED = (
    "u21", "u 21", "paf", "a2 ligi", "akademi", "gelisim", "gelişim", "elit u",
    "u19", "u 19", "u18", "u 18", "u17", "u 17", "u16", "u 16", "u15", "u 15",
    "u14", "u 14", "bolgesel amator", "bölgesel amatör", "bal takimi", "bal takımı",
    "rezerv", "kadin", "kadın", "futsal",
)


def match_type(m: dict[str, Any]) -> str:
    return str(m.get("matchType") or m.get("type") or "league")


def validate_season(season_dir: Path, min_matches: int, min_league: int, max_matches: int) -> dict[str, Any]:
    sid = season_dir.name
    idx = season_dir / "matches_index.json"
    arr = read_json(idx, []) if idx.exists() else []
    if not isinstance(arr, list):
        arr = []
    problems: list[str] = []
    comps = sorted({str(m.get("competition") or "") for m in arr if isinstance(m, dict)})
    total = len(arr)
    league = sum(1 for m in arr if isinstance(m, dict) and match_type(m) == "league")
    if total < min_matches:
        problems.append(f"too_few_matches:{total}")
    if league < min_league:
        problems.append(f"too_few_league_matches:{league}")
    if total > max_matches:
        problems.append(f"too_many_matches:{total}")
    bad_comps = [c for c in comps if any(norm(x) in norm(c) for x in BANNED)]
    if bad_comps:
        problems.append("non_senior_competitions_present")
    missing_balkes = 0
    bad_scores = 0
    for m in arr:
        if not isinstance(m, dict):
            continue
        if not (is_balkes(m.get("homeTeam")) or is_balkes(m.get("awayTeam"))):
            missing_balkes += 1
        s = m.get("score") or {}
        if s.get("played") and (s.get("home") is None or s.get("away") is None):
            bad_scores += 1
    if missing_balkes:
        problems.append(f"matches_without_balkes:{missing_balkes}")
    if bad_scores:
        problems.append(f"played_without_score:{bad_scores}")
    standings_path = season_dir / "standings_by_week.json"
    standings_weeks = 0
    if standings_path.exists():
        st = read_json(standings_path, [])
        standings_weeks = len(st) if isinstance(st, list) else 0
    return {
        "season": sid,
        "matches": total,
        "leagueMatches": league,
        "standingsWeeks": standings_weeks,
        "competitions": comps,
        "badCompetitions": bad_comps,
        "status": "ok" if not problems else "problem",
        "problems": problems,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data", type=Path)
    ap.add_argument("--reports-root", default="reports/tff_factory", type=Path)
    ap.add_argument("--start-season", default="")
    ap.add_argument("--max-seasons", type=int, default=0)
    ap.add_argument("--min-matches", type=int, default=8)
    ap.add_argument("--min-league-matches", type=int, default=8)
    ap.add_argument("--max-matches", type=int, default=80)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    seasons_root = args.data_root / "seasons"
    results = []
    if seasons_root.exists():
        for season_dir in sorted([p for p in seasons_root.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True):
            results.append(validate_season(season_dir, args.min_matches, args.min_league_matches, args.max_matches))
    summary = {
        "status": "ok" if all(r["status"] == "ok" for r in results) else "problem",
        "publishedSeasons": len(results),
        "problemSeasons": [r for r in results if r["status"] != "ok"],
        "seasons": results,
    }
    args.reports_root.mkdir(parents=True, exist_ok=True)
    write_json(args.reports_root / "target_validation_v33.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.strict and summary["problemSeasons"]:
        raise SystemExit(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

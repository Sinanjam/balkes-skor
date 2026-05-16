#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

BANNED = (
    "u21", "u 21", "paf", "akademi", "gelisim", "gelişim", "elit u", "u19", "u 19",
    "u18", "u 18", "u17", "u 17", "u16", "u 16", "u15", "u 15", "u14", "u 14",
    "bolgesel amator", "bölgesel amatör", "bal takimi", "bal takımı", "rezerv", "kadin", "kadın", "futsal",
)


def norm(s: Any) -> str:
    text = str(s or "").lower()
    repl = str.maketrans("çğıöşüı", "cgiosui")
    text = text.translate(repl)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def is_bad_competition(comp: str) -> bool:
    n = norm(comp)
    return any(norm(x) in n for x in BANNED)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data", type=Path)
    ap.add_argument("--reports-root", default="reports/tff_factory", type=Path)
    ap.add_argument("--start-season", default="")
    ap.add_argument("--max-seasons", type=int, default=0)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    manifest = read_json(args.data_root / "manifest.json", {})
    seasons = manifest.get("availableSeasons") or [] if isinstance(manifest, dict) else []
    problems: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    if not seasons:
        problems.append({"season": "_global", "problems": ["no_published_seasons"]})
    for s in seasons:
        season = s.get("id") or s.get("season")
        if not season:
            continue
        idx = read_json(args.data_root / "seasons" / season / "matches_index.json", [])
        standings = read_json(args.data_root / "seasons" / season / "standings_by_week.json", [])
        if not isinstance(idx, list): idx = []
        if not isinstance(standings, list): standings = []
        comps = sorted({str(m.get("competition") or "") for m in idx if isinstance(m, dict)})
        bad = [c for c in comps if is_bad_competition(c)]
        ids = [str(m.get("id")) for m in idx if isinstance(m, dict)]
        dupes = sorted([x for x in set(ids) if ids.count(x) > 1])
        league = sum(1 for m in idx if isinstance(m, dict) and str(m.get("matchType") or m.get("type") or "league") == "league")
        row = {
            "season": season,
            "matches": len(idx),
            "leagueMatches": league,
            "standingsWeeks": len(standings),
            "competitions": comps,
            "badCompetitions": bad,
            "duplicateMatchIds": dupes[:20],
            "status": "ok",
            "problems": [],
        }
        if len(idx) == 0: row["problems"].append("empty_matches")
        if len(idx) > 90: row["problems"].append(f"too_many_matches:{len(idx)}")
        if len(idx) < 8: row["problems"].append(f"too_few_matches:{len(idx)}")
        if league < 8: row["problems"].append(f"too_few_league_matches:{league}")
        if bad: row["problems"].append("bad_competition_tokens")
        if dupes: row["problems"].append("duplicate_match_ids")
        # Standings are not required for current/unplanned season; they are warnings only.
        if row["problems"]:
            row["status"] = "problem"
            problems.append(row)
        results.append(row)
    out = {"status": "ok" if not problems else "problem", "publishedSeasons": len(seasons), "problemSeasons": problems, "seasons": results}
    args.reports_root.mkdir(parents=True, exist_ok=True)
    (args.reports_root / "target_validation_v35.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.strict and problems:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

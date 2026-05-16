#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "v3.5-summary-standings-reconcile"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def write_json(path: Path, obj: Any, write: bool) -> None:
    if not write:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def match_type(m: dict[str, Any]) -> str:
    return str(m.get("matchType") or m.get("type") or "league")


def match_stats(matches: list[dict[str, Any]], league_only: bool = False) -> dict[str, Any]:
    wins = draws = losses = gf = ga = played = 0
    type_counts: Counter[str] = Counter()
    for m in matches:
        mt = match_type(m)
        type_counts[mt] += 1
        if league_only and mt != "league":
            continue
        score = m.get("score") or {}
        if not score.get("played"):
            continue
        b = m.get("balkes") or {}
        res = b.get("result") or ""
        if res not in {"W", "D", "L"}:
            continue
        played += 1
        if res == "W":
            wins += 1
        elif res == "D":
            draws += 1
        elif res == "L":
            losses += 1
        if b.get("goalsFor") is not None:
            gf += int(b.get("goalsFor") or 0)
        if b.get("goalsAgainst") is not None:
            ga += int(b.get("goalsAgainst") or 0)
    return {
        "matches": len([m for m in matches if (not league_only or match_type(m) == "league")]),
        "played": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goalsFor": gf,
        "goalsAgainst": ga,
        "goalDifference": gf - ga,
        "pointsFromResults": wins * 3 + draws,
        "matchTypes": dict(type_counts),
    }


def final_balkes_table(standings: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not standings:
        return None
    for week in reversed(standings):
        rows = week.get("standings") or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if row.get("isBalkes"):
                return dict(row)
            team = str(row.get("team") or "").lower()
            if "balıkesir" in team or "balikesir" in team:
                x = dict(row); x["isBalkes"] = True; return x
    return None


def normalize_table_row(row: dict[str, Any], league_stats: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    table = {
        "rank": row.get("rank"),
        "team": row.get("team"),
        "played": row.get("played"),
        "won": row.get("won"),
        "drawn": row.get("drawn"),
        "lost": row.get("lost"),
        "goalsFor": row.get("goalsFor"),
        "goalsAgainst": row.get("goalsAgainst"),
        "goalDifference": row.get("goalDifference"),
        "points": row.get("points"),
        "rawPoints": row.get("rawPoints"),
        "pointsDeducted": row.get("pointsDeducted") or 0,
        "penaltyNote": row.get("penaltyNote") or "",
        "source": "official_tff_weekly_table",
    }
    result_points = int(league_stats.get("pointsFromResults") or 0)
    table_points = int(table.get("points") or 0)
    if result_points > table_points:
        inferred = result_points - table_points
        # Existing builder sometimes leaves pointsDeducted=0 although official table is lower.
        if int(table.get("pointsDeducted") or 0) < inferred:
            table["pointsDeducted"] = inferred
            table["rawPoints"] = result_points
            table["penaltyNote"] = f"v3.5 inferred from official table: {inferred} point deduction"
            warnings.append(f"inferred_points_deduction:{inferred}")
    comparisons = [
        ("played", "played"),
        ("won", "wins"),
        ("drawn", "draws"),
        ("lost", "losses"),
        ("goalsFor", "goalsFor"),
        ("goalsAgainst", "goalsAgainst"),
        ("goalDifference", "goalDifference"),
    ]
    mismatches: list[str] = []
    for table_key, stat_key in comparisons:
        tv = table.get(table_key)
        sv = league_stats.get(stat_key)
        if tv is not None and sv is not None and int(tv) != int(sv):
            mismatches.append(f"{table_key}:table={tv},matches={sv}")
    if mismatches:
        warnings.append("official_table_differs_from_match_index:" + ";".join(mismatches))
    return table, warnings


def process_season(season_dir: Path, write: bool) -> dict[str, Any] | None:
    season = season_dir.name
    idx_path = season_dir / "matches_index.json"
    idx = read_json(idx_path, [])
    if not isinstance(idx, list) or not idx:
        return None
    standings = read_json(season_dir / "standings_by_week.json", [])
    if not isinstance(standings, list):
        standings = []
    all_stats = match_stats(idx, league_only=False)
    league_stats = match_stats(idx, league_only=True)
    summary: dict[str, Any] = {
        "matches": all_stats["matches"],
        "played": all_stats["played"],
        "wins": all_stats["wins"],
        "draws": all_stats["draws"],
        "losses": all_stats["losses"],
        "goalsFor": all_stats["goalsFor"],
        "goalsAgainst": all_stats["goalsAgainst"],
        "goalDifference": all_stats["goalDifference"],
        "matchTypes": all_stats["matchTypes"],
        "leagueMatchStats": league_stats,
    }
    warnings: list[str] = []
    table_row = final_balkes_table(standings)
    if table_row:
        table, ws = normalize_table_row(table_row, league_stats)
        warnings.extend(ws)
        summary["leagueTable"] = table
        # Keep legacy fields useful for the current app, but now derive them consistently from the official table.
        summary["points"] = table.get("points")
        summary["rawPoints"] = table.get("rawPoints")
        summary["pointsDeducted"] = table.get("pointsDeducted")
        summary["finalRank"] = table.get("rank")
    if warnings:
        summary["warnings"] = warnings

    season_json = read_json(season_dir / "season.json", {})
    if not isinstance(season_json, dict):
        season_json = {}
    season_json["summary"] = summary
    season_json["factoryVersion"] = VERSION
    season_json["updatedAt"] = now()
    season_json.setdefault("files", {})["matchesIndex"] = f"seasons/{season}/matches_index.json"
    season_json.setdefault("files", {})["standingsByWeek"] = f"seasons/{season}/standings_by_week.json"
    write_json(season_dir / "season.json", season_json, write)
    return {
        "id": season,
        "name": season,
        "matchCount": len(idx),
        "competition": season_json.get("competition") or (idx[0].get("competition") if idx else ""),
        "summary": summary,
        "standingsByWeekUrl": f"seasons/{season}/standings_by_week.json",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data", type=Path)
    ap.add_argument("--reports-root", default="reports/tff_factory", type=Path)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    seasons_root = args.data_root / "seasons"
    seasons: list[dict[str, Any]] = []
    if seasons_root.exists():
        for season_dir in sorted([p for p in seasons_root.iterdir() if p.is_dir()], reverse=True):
            item = process_season(season_dir, args.write)
            if item:
                seasons.append(item)
    total_matches = sum(int(s.get("matchCount") or 0) for s in seasons)
    manifest = read_json(args.data_root / "manifest.json", {})
    if not isinstance(manifest, dict):
        manifest = {}
    manifest.update({
        "app": manifest.get("app") or "Balkes Skor",
        "schemaVersion": 3,
        "dataVersion": 1,
        "generatedAt": now(),
        "team": manifest.get("team") or "Balıkesirspor",
        "availableSeasons": seasons,
        "global": manifest.get("global") or {
            "playersIndexUrl": "players_index.json",
            "opponentsIndexUrl": "opponents_index.json",
            "searchIndexUrl": "search_index.json",
            "dataReportUrl": "data_report.json",
        },
        "dataBaseUrl": manifest.get("dataBaseUrl") or "https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/",
        "factoryVersion": VERSION,
        "targetedSeniorProfessionalGuard": True,
        "safeToPush": bool(seasons and total_matches),
    })
    report = {
        "generatedAt": now(),
        "sourcePolicy": "TFF senior professional target only",
        "factoryVersion": VERSION,
        "totalAppMatches": total_matches,
        "seasons": seasons,
        "notes": [
            "v3.5 keeps match-derived season stats separate from official league-table stats.",
            "If official points are lower than match-result points, the deduction is inferred and reported.",
            "Empty manifests are not safe to push.",
        ],
        "safeToPush": bool(seasons and total_matches),
    }
    write_json(args.data_root / "manifest.json", manifest, args.write)
    write_json(args.data_root / "data_report.json", report, args.write)
    args.reports_root.mkdir(parents=True, exist_ok=True)
    write_json(args.reports_root / "reconcile_v35_summary.json", report, args.write)
    print(json.dumps({"write": args.write, "seasons": len(seasons), "totalMatches": total_matches, "safeToPush": bool(seasons and total_matches)}, ensure_ascii=False, indent=2))
    for s in seasons:
        warnings = (s.get("summary") or {}).get("warnings") or []
        if warnings:
            print(f"warning {s['id']}: " + " | ".join(warnings))
    return 0 if seasons and total_matches else 2


if __name__ == "__main__":
    raise SystemExit(main())

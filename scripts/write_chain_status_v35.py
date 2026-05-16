#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--reports-root", default="reports/tff_chain")
ap.add_argument("--chain-label", required=True)
ap.add_argument("--group-name", required=True)
ap.add_argument("--start-season", required=True)
ap.add_argument("--max-seasons", type=int, required=True)
ap.add_argument("--status", required=True)
ap.add_argument("--exit-code", type=int, required=True)
ap.add_argument("--skip-standings", default="false")
args = ap.parse_args()
root = Path(args.reports_root)
root.mkdir(parents=True, exist_ok=True)
name = f"{args.chain_label}_{args.group_name}.json".replace("/", "_").replace(" ", "_")
obj = {
    "chainLabel": args.chain_label,
    "group": args.group_name,
    "startSeason": args.start_season,
    "maxSeasons": args.max_seasons,
    "status": args.status,
    "exitCode": args.exit_code,
    "skipStandings": args.skip_standings,
    "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}
path = root / name
path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"chain status file: {path} {obj}")

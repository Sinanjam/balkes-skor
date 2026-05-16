#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--field", choices=["seasons", "matches"], required=True)
ap.add_argument("--data-root", default="data")
args = ap.parse_args()
root = Path(args.data_root)
try:
    if args.field == "seasons":
        obj = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        print(len(obj.get("availableSeasons") or []))
    else:
        obj = json.loads((root / "data_report.json").read_text(encoding="utf-8"))
        print(int(obj.get("totalAppMatches") or 0))
except Exception:
    print(0)

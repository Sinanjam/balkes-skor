#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--trigger", default=".github/tff-chain-v34-trigger.json")
ap.add_argument("--next-start", required=True)
ap.add_argument("--last-group", default="")
ap.add_argument("--last-status", default="")
args = ap.parse_args()

p = Path(args.trigger)
obj = {}
if p.exists():
    try:
        loaded = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            obj.update(loaded)
    except Exception:
        pass
obj["start_season"] = args.next_start
obj["clean_all_before_start"] = False
obj["last_group"] = args.last_group
obj["last_status"] = args.last_status
obj["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"next trigger written: {p} -> {args.next_start}")

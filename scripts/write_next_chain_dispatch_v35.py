#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULTS = {
    "end_year": 1990,
    "group_size": 4,
    "wait_minutes": 5,
    "group_timeout_minutes": 300,
    "clean_all_before_start": False,
    "auto_push_main": True,
    "skip_standings": False,
    "standings_mode": "auto",
    "standings_detail_mode": "missing",
    "standings_workers": 6,
    "standings_week_param_mode": "smart",
    "legacy_broad_probe_limit": 350,
    "strict_legacy_targets": True,
    "chain_label": "chain-1991-v35-dispatch",
}


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def load_json(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


ap = argparse.ArgumentParser()
ap.add_argument("--trigger", default=".github/tff-chain-v35-trigger.json")
ap.add_argument("--out", default="/tmp/tff-chain-v35-dispatch.json")
ap.add_argument("--event-type", default="tff-chain-v35")
ap.add_argument("--next-start", required=True)
ap.add_argument("--last-group", default="")
ap.add_argument("--last-status", default="")
args = ap.parse_args()

cfg = dict(DEFAULTS)
cfg.update({k: v for k, v in load_json(args.trigger).items() if v is not None})
# Sonraki grupte temizlik kesinlikle false olmalı; ilk run zaten data'yı temizledi.
cfg["start_season"] = args.next_start
cfg["clean_all_before_start"] = False
cfg["last_group"] = args.last_group
cfg["last_status"] = args.last_status
cfg["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

for key in ["clean_all_before_start", "auto_push_main", "skip_standings", "strict_legacy_targets"]:
    cfg[key] = as_bool(cfg.get(key, DEFAULTS.get(key, False)))
for key in ["end_year", "group_size", "wait_minutes", "group_timeout_minutes", "standings_workers", "legacy_broad_probe_limit"]:
    cfg[key] = int(cfg.get(key, DEFAULTS[key]))

payload = {"event_type": args.event_type, "client_payload": cfg}
p = Path(args.out)
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"dispatch payload written: {p} -> {args.next_start}")

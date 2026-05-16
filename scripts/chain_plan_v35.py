#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

DEFAULTS = {
    "start_season": "2025-2026",
    "end_year": 1990,
    "group_size": 4,
    "wait_minutes": 5,
    "group_timeout_minutes": 300,
    "clean_all_before_start": True,
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


def out(key: str, value: Any) -> None:
    if isinstance(value, bool):
        value = "true" if value else "false"
    print(f"{key}={value}")


def load_trigger_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except Exception as exc:
        raise SystemExit(f"Trigger JSON okunamadı: {path}: {exc}")


def load_dispatch_payload() -> dict[str, Any]:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if event_name != "repository_dispatch" or not event_path:
        return {}
    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"repository_dispatch event okunamadı: {event_path}: {exc}")
    payload = event.get("client_payload") or {}
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trigger", default=".github/tff-chain-v35-trigger.json")
    args = ap.parse_args()

    cfg = dict(DEFAULTS)
    # Push ile ilk başlatmada dosyadan oku. Sonraki gruplarda repository_dispatch payload'ı dosyadan üstündür.
    cfg.update({k: v for k, v in load_trigger_file(Path(args.trigger)).items() if v is not None})
    cfg.update({k: v for k, v in load_dispatch_payload().items() if v is not None})

    start = str(cfg["start_season"])
    m = re.match(r"^(\d{4})-(\d{4})$", start)
    if not m:
        raise SystemExit(f"start_season formatı hatalı: {start}")
    y = int(m.group(1))
    end_year = int(cfg["end_year"])
    group_size = int(cfg["group_size"])
    seasons: list[str] = []
    for yy in range(y, max(end_year, y - group_size + 1) - 1, -1):
        seasons.append(f"{yy}-{yy+1}")
    if not seasons:
        raise SystemExit("Planlanacak sezon yok")
    next_y = y - group_size
    has_next = next_y >= end_year
    next_start = f"{next_y}-{next_y+1}" if has_next else ""

    out("max_seasons", len(seasons))
    out("group_start", seasons[0])
    out("group_end", seasons[-1])
    out("group_name", f"{seasons[0]}..{seasons[-1]}")
    out("has_next", has_next)
    out("next_start", next_start)

    for key in [
        "start_season", "end_year", "group_size", "wait_minutes", "group_timeout_minutes",
        "clean_all_before_start", "auto_push_main", "skip_standings", "standings_mode",
        "standings_detail_mode", "standings_workers", "standings_week_param_mode",
        "legacy_broad_probe_limit", "strict_legacy_targets", "chain_label",
    ]:
        val = cfg.get(key, DEFAULTS[key])
        if key in {"clean_all_before_start", "auto_push_main", "skip_standings", "strict_legacy_targets"}:
            val = as_bool(val)
        out(key, val)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

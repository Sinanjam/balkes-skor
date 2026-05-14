#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import argparse, shutil, json
from datetime import datetime, timezone

def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def write(path, obj):
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data")
    args=ap.parse_args()
    root=Path(args.data_root)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    write(root/"manifest.json", {
        "app":"Balkes Skor",
        "schemaVersion":3,
        "dataVersion":1,
        "generatedAt":now(),
        "team":"Balıkesirspor",
        "availableSeasons":[],
        "global":{
            "playersIndexUrl":"players_index.json",
            "opponentsIndexUrl":"opponents_index.json",
            "searchIndexUrl":"search_index.json",
            "dataReportUrl":"data_report.json"
        },
        "factoryVersion":"v2.2-manual-clean-db",
        "dataBaseUrl":"https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/"
    })
    write(root/"players_index.json", [])
    write(root/"opponents_index.json", [])
    write(root/"search_index.json", [])
    write(root/"data_report.json", {
        "generatedAt":now(),
        "sourcePolicy":"TFF-only",
        "factoryVersion":"v2.2-manual-clean-db",
        "totalAppMatches":0,
        "seasons":[],
        "notes":["Clean database initialized."]
    })
    print(f"Clean database initialized at {root}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import shutil
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-data", default="data")
    ap.add_argument("--web-data", required=True)
    args = ap.parse_args()

    app = Path(args.app_data)
    web = Path(args.web_data)

    if not (app / "manifest.json").exists():
        raise SystemExit(f"app data yok: {app}")
    if web.exists():
        shutil.rmtree(web)
    shutil.copytree(app, web)

    man_path = web / "manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    man["dataBaseUrl"] = "https://raw.githubusercontent.com/Sinanjam/balkes-skor-web/main/docs/data/"
    man_path.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"web data synced: {web}")

if __name__ == "__main__":
    main()

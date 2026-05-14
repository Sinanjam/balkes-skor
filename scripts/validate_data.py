#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
from pathlib import Path

def read(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--min-seasons", type=int, default=12)
    ap.add_argument("--min-matches", type=int, default=177)
    args = ap.parse_args()

    root = Path(args.data_root)
    manifest = read(root / "manifest.json")
    seasons = manifest.get("availableSeasons", [])

    if len(seasons) < args.min_seasons:
        raise SystemExit(f"HATA: sezon sayısı düştü: {len(seasons)} < {args.min_seasons}")

    total = sum(int(s.get("matchCount") or 0) for s in seasons)
    if total < args.min_matches:
        raise SystemExit(f"HATA: maç sayısı düştü: {total} < {args.min_matches}")

    bad = []
    for s in seasons:
        sid = s.get("id")
        idx_path = root / "seasons" / sid / "matches_index.json"
        if not idx_path.exists():
            bad.append(f"{sid}: matches_index yok")
            continue

        arr = read(idx_path)
        if not isinstance(arr, list):
            bad.append(f"{sid}: matches_index liste değil")
            continue

        if len(arr) != int(s.get("matchCount") or 0):
            bad.append(f"{sid}: manifest={s.get('matchCount')} index={len(arr)}")

        for m in arr:
            if not isinstance(m, dict):
                bad.append(f"{sid}: bozuk maç objesi")
                continue
            for key in ["id", "homeTeam", "awayTeam", "source"]:
                if key not in m:
                    bad.append(f"{sid}:{m.get('id')} {key} eksik")
            src = m.get("source") or {}
            if src.get("name") != "TFF":
                bad.append(f"{sid}:{m.get('id')} TFF dışı source")
            if not src.get("url"):
                bad.append(f"{sid}:{m.get('id')} source.url eksik")

    if bad:
        print("\n".join(bad[:300]))
        raise SystemExit(f"HATA: {len(bad)} validasyon sorunu")

    print(f"OK: {len(seasons)} sezon / {total} maç / TFF-only güvenli")

if __name__ == "__main__":
    main()

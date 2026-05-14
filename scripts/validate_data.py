#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, json
from pathlib import Path

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def sig(m):
    b=m.get("balkes") or {}
    score=m.get("score") or {}
    return "|".join([
        str(m.get("date") or ""),
        str(b.get("opponent") or m.get("homeTeam") or m.get("awayTeam") or "").lower(),
        "home" if b.get("isHome") else "away",
        str(score.get("display") or "")
    ])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--min-seasons", type=int, default=1)
    ap.add_argument("--min-matches", type=int, default=1)
    args=ap.parse_args()
    root=Path(args.data_root)
    manifest=read(root/"manifest.json")
    seasons=manifest.get("availableSeasons", [])
    if len(seasons) < args.min_seasons:
        raise SystemExit(f"HATA: sezon sayısı düşük: {len(seasons)} < {args.min_seasons}")
    total=sum(int(s.get("matchCount") or 0) for s in seasons)
    if total < args.min_matches:
        raise SystemExit(f"HATA: maç sayısı düşük: {total} < {args.min_matches}")
    errors=[]
    all_sigs={}
    for s in seasons:
        sid=s.get("id")
        p=root/"seasons"/sid/"matches_index.json"
        if not p.exists():
            errors.append(f"{sid}: matches_index yok")
            continue
        arr=read(p)
        if not isinstance(arr, list):
            errors.append(f"{sid}: matches_index liste değil")
            continue
        if len(arr) != int(s.get("matchCount") or 0):
            errors.append(f"{sid}: manifest={s.get('matchCount')} index={len(arr)}")
        ids=set()
        for m in arr:
            if not isinstance(m, dict):
                errors.append(f"{sid}: bozuk maç objesi")
                continue
            mid=str(m.get("id") or "")
            if not mid:
                errors.append(f"{sid}: maç id yok")
            if mid in ids:
                errors.append(f"{sid}: duplicate macId {mid}")
            ids.add(mid)
            source=m.get("source") or {}
            if source.get("name") != "TFF" or not source.get("url"):
                errors.append(f"{sid}:{mid}: TFF source/url eksik")
            detail=root/(m.get("detailUrl") or "")
            if not detail.exists():
                errors.append(f"{sid}:{mid}: detail dosyası yok {detail}")
            sg=sig(m)
            if sg in all_sigs:
                errors.append(f"{sid}:{mid}: duplicate signature with {all_sigs[sg]}")
            all_sigs[sg]=f"{sid}:{mid}"
    if errors:
        print("\n".join(errors[:300]))
        raise SystemExit(f"HATA: {len(errors)} validasyon sorunu")
    print(f"OK: {len(seasons)} sezon / {total} maç / duplicate yok / TFF-only")

if __name__=="__main__":
    main()

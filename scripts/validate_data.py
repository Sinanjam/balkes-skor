#!/usr/bin/env python3
import argparse,json
from pathlib import Path
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--data-root",default="data"); ap.add_argument("--min-seasons",type=int,default=1); ap.add_argument("--min-matches",type=int,default=1); args=ap.parse_args()
    root=Path(args.data_root); manifest=read(root/"manifest.json"); seasons=manifest.get("availableSeasons",[])
    total=sum(int(s.get("matchCount") or 0) for s in seasons)
    if len(seasons)<args.min_seasons: raise SystemExit(f"HATA: sezon sayısı düşük: {len(seasons)} < {args.min_seasons}")
    if total<args.min_matches: raise SystemExit(f"HATA: maç sayısı düşük: {total} < {args.min_matches}")
    errs=[]
    for s in seasons:
        sid=s["id"]; arr=read(root/"seasons"/sid/"matches_index.json")
        if len(arr)!=int(s.get("matchCount") or 0): errs.append(f"{sid}: manifest/index uyuşmuyor")
        ids=set()
        for m in arr:
            mid=str(m.get("id") or "")
            if mid in ids: errs.append(f"{sid}: duplicate id {mid}")
            ids.add(mid)
            if (m.get("source") or {}).get("name")!="TFF": errs.append(f"{sid}:{mid}: TFF source yok")
            if not (root/(m.get("detailUrl") or "")).exists(): errs.append(f"{sid}:{mid}: detail yok")
    if errs:
        print("\n".join(errs[:200])); raise SystemExit(f"HATA: {len(errs)} validasyon sorunu")
    print(f"OK: {len(seasons)} sezon / {total} maç")
if __name__=="__main__": main()

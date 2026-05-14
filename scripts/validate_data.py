#!/usr/bin/env python3
import argparse,json
from pathlib import Path
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--data-root',default='data'); ap.add_argument('--min-seasons',type=int,default=12); ap.add_argument('--min-matches',type=int,default=177); a=ap.parse_args(); root=Path(a.data_root)
    m=read(root/'manifest.json'); ss=m.get('availableSeasons',[]); total=sum(int(s.get('matchCount') or 0) for s in ss)
    if len(ss)<a.min_seasons: raise SystemExit(f'HATA: sezon sayısı düştü: {len(ss)} < {a.min_seasons}')
    if total<a.min_matches: raise SystemExit(f'HATA: maç sayısı düştü: {total} < {a.min_matches}')
    bad=[]
    for s in ss:
        sid=s.get('id'); p=root/'seasons'/sid/'matches_index.json'
        if not p.exists(): bad.append(f'{sid}: matches_index yok'); continue
        arr=read(p)
        if len(arr)!=int(s.get('matchCount') or 0): bad.append(f'{sid}: manifest={s.get("matchCount")} index={len(arr)}')
        for m in arr:
            src=m.get('source') or {}
            if src.get('name')!='TFF': bad.append(f'{sid}:{m.get("id")} TFF dışı source')
            if not src.get('url'): bad.append(f'{sid}:{m.get("id")} source.url eksik')
    if bad:
        print('\n'.join(bad[:300])); raise SystemExit(f'HATA: {len(bad)} validasyon sorunu')
    print(f'OK: {len(ss)} sezon / {total} maç / TFF-only güvenli')
if __name__=='__main__': main()

#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from typing import Any
DEFAULTS={"seasons":[],"auto_push_main":True,"skip_standings":False,"standings_mode":"auto","standings_detail_mode":"missing","standings_workers":6,"standings_week_param_mode":"smart","legacy_broad_probe_limit":350,"strict_legacy_targets":True,"allow_partial":True,"chain_label":"repair-v37-exact-seasons"}
def as_bool(v:Any)->bool:
    return v if isinstance(v,bool) else str(v).strip().lower() in {"1","true","yes","y","on"}
def parse_seasons(v:Any)->list[str]:
    raw=[]
    if isinstance(v,list):
        for x in v: raw.extend(parse_seasons(x))
    else:
        raw=re.split(r"[\s,;]+", str(v or '').strip())
    out=[]; seen=set()
    for item in raw:
        if not item: continue
        if not re.match(r"^\d{4}-\d{4}$", item): raise SystemExit(f"Sezon formatı hatalı: {item}")
        if item not in seen: seen.add(item); out.append(item)
    return out
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--trigger',default='.github/tff-repair-v37-trigger.json'); args=ap.parse_args()
    p=Path(args.trigger)
    if not p.exists(): raise SystemExit(f"Trigger bulunamadı: {p}")
    cfg=dict(DEFAULTS); loaded=json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(loaded,dict): raise SystemExit('Trigger JSON object olmalı')
    cfg.update({k:v for k,v in loaded.items() if v is not None})
    seasons=sorted(parse_seasons(cfg.get('seasons')), key=lambda s:int(s[:4]), reverse=True)
    if not seasons: raise SystemExit('Trigger içinde seasons boş. Örn: "2024-2025,2023-2024"')
    def out(k,v):
        if isinstance(v,bool): v='true' if v else 'false'
        print(f'{k}={v}')
    out('seasons_csv', ','.join(seasons)); out('season_count', len(seasons)); out('group_name', f'{seasons[0]}..{seasons[-1]}' if len(seasons)>1 else seasons[0])
    for key in ['auto_push_main','skip_standings','standings_mode','standings_detail_mode','standings_workers','standings_week_param_mode','legacy_broad_probe_limit','strict_legacy_targets','allow_partial','chain_label']:
        val=cfg.get(key, DEFAULTS[key])
        if key in {'auto_push_main','skip_standings','strict_legacy_targets','allow_partial'}: val=as_bool(val)
        out(key,val)
    return 0
if __name__=='__main__': raise SystemExit(main())

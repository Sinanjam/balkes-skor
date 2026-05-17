#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,shutil,subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
DEFAULTS={"seasons":[],"skip_standings":False,"standings_mode":"auto","standings_detail_mode":"missing","standings_workers":6,"standings_week_param_mode":"smart","legacy_broad_probe_limit":350,"strict_legacy_targets":True,"allow_partial":True,"chain_label":"repair-v37-exact-seasons"}
def as_bool(v:Any)->bool: return v if isinstance(v,bool) else str(v).strip().lower() in {"1","true","yes","y","on"}
def parse_seasons(v:Any)->list[str]:
    parts=[]
    if isinstance(v,list):
        for x in v: parts.extend(parse_seasons(x))
    else: parts=re.split(r"[\s,;]+", str(v or '').strip())
    out=[]; seen=set()
    for item in parts:
        if not item: continue
        if not re.match(r"^\d{4}-\d{4}$",item): raise SystemExit(f"Sezon formatı hatalı: {item}")
        if item not in seen: seen.add(item); out.append(item)
    return sorted(out,key=lambda s:int(s[:4]),reverse=True)
def run(cmd:list[str], check:bool=False)->int:
    print('+',' '.join(cmd),flush=True); cp=subprocess.run(cmd)
    if check and cp.returncode!=0: raise subprocess.CalledProcessError(cp.returncode,cmd)
    return cp.returncode
def copy_season(src_root:Path,dst_parent:Path,season:str)->bool:
    src=src_root/'seasons'/season
    if not (src/'season.json').exists(): return False
    dst=dst_parent/season
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src,dst); return True
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--trigger',default='.github/tff-repair-v37-trigger.json'); ap.add_argument('--data-root',default='data'); ap.add_argument('--raw-root',default='sources/tff/raw'); ap.add_argument('--standings-raw-root',default='sources/tff/standings_raw'); ap.add_argument('--reports-root',default='reports/tff_repair_v37'); args=ap.parse_args()
    cfg=dict(DEFAULTS); loaded=json.loads(Path(args.trigger).read_text(encoding='utf-8'))
    if not isinstance(loaded,dict): raise SystemExit('Trigger JSON object olmalı')
    cfg.update({k:v for k,v in loaded.items() if v is not None}); seasons=parse_seasons(cfg.get('seasons'))
    if not seasons: raise SystemExit('İşlenecek sezon yok')
    data_root=Path(args.data_root); reports_root=Path(args.reports_root); reports_root.mkdir(parents=True, exist_ok=True)
    backup=Path('/tmp/balkes_v37_pre_repair_data'); staging_parent=Path('/tmp/balkes_v37_staging'); staging=staging_parent/'seasons'
    for p in [backup,staging_parent]:
        if p.exists(): shutil.rmtree(p)
    staging.mkdir(parents=True)
    existing=[]
    if data_root.exists():
        shutil.copytree(data_root,backup)
        existing=sorted([p.name for p in (backup/'seasons').iterdir() if p.is_dir()] if (backup/'seasons').exists() else [], key=lambda s:int(s[:4]), reverse=True)
        for sid in existing: copy_season(backup, staging, sid)
    statuses={}; standings_script='scripts/tff_standings_builder_v31.py' if Path('scripts/tff_standings_builder_v31.py').exists() else 'scripts/tff_standings_builder.py'
    for season in seasons:
        print(f'=== v3.7 exact repair: {season} ===',flush=True)
        strict_arg='--strict-legacy-targets' if as_bool(cfg.get('strict_legacy_targets',True)) else '--no-strict-legacy-targets'
        status={'factoryExit':None,'standingsExit':None,'published':False}
        code=run(['python','scripts/tff_factory_v37_targeted_professional.py','--seed','sources/tff/registry/balkes_tff_seed_registry.json','--data-root',str(data_root),'--raw-root',args.raw_root,'--reports-root','reports/tff_factory','--start-season',season,'--max-seasons','1','--sleep','1.0','--max-discovery-probe','1500','--legacy-broad-probe-limit',str(int(cfg.get('legacy_broad_probe_limit',350))),strict_arg,'--skip-standings'])
        status['factoryExit']=code
        run(['python','scripts/clean_bad_professional_data_v33.py','--data-root',str(data_root),'--reports-root','reports/tff_factory','--write'])
        if code==0 and not as_bool(cfg.get('skip_standings',False)):
            scode=run(['python',standings_script,'--seed','sources/tff/registry/balkes_tff_seed_registry.json','--data-root',str(data_root),'--raw-root',args.standings_raw_root,'--reports-root','reports/standings','--penalties','data/standings_penalties.json','--start-season',season,'--max-seasons','1','--mode',str(cfg.get('standings_mode','auto')),'--probe-limit','5000','--workers',str(int(cfg.get('standings_workers',6))),'--detail-fetch-mode',str(cfg.get('standings_detail_mode','missing')),'--week-param-mode',str(cfg.get('standings_week_param_mode','smart')),'--sleep','0.15'])
            status['standingsExit']=scode
        if copy_season(data_root,staging,season): status['published']=True
        elif copy_season(backup,staging,season): status['published']=True; status['fromBackup']=True
        statuses[season]=status
    target=data_root/'seasons'
    if target.exists(): shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True); shutil.copytree(staging,target)
    run(['python','scripts/rebuild_data_indexes_v37.py','--data-root',str(data_root),'--factory-version','v3.7-exact-season-repair'],check=True)
    final=json.loads((data_root/'manifest.json').read_text(encoding='utf-8')); published=[s['id'] for s in final.get('availableSeasons',[])]
    reqpub=[s for s in seasons if s in published]; missing=[s for s in seasons if s not in published]
    summary={'generatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'requested':seasons,'existingBefore':existing,'publishedAfter':published,'requestedPublished':reqpub,'missingRequested':missing,'statuses':statuses,'safeToPush':bool(published) and bool(reqpub),'allowPartial':as_bool(cfg.get('allow_partial',True))}
    (reports_root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(summary,ensure_ascii=False,indent=2))
    if not summary['safeToPush']: raise SystemExit('Hiçbir hedef sezon yayınlanabilir hale gelmedi; push güvenli değil.')
    if missing and not summary['allowPartial']: raise SystemExit(f'Eksik hedef sezon var ve allow_partial=false: {missing}')
    return 0
if __name__=='__main__': raise SystemExit(main())

#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from datetime import datetime,timezone
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def read(p,d):
    try: return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception: return d
def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('cmd',choices=['claim','complete','reset']); ap.add_argument('--seed',default='sources/tff/registry/balkes_tff_seed_registry.json'); ap.add_argument('--state',default='sources/tff/state/season_queue.json'); ap.add_argument('--claim-file',default='reports/tff_factory/queue_claim.json'); ap.add_argument('--start-season',default='auto'); a=ap.parse_args()
    seed=read(a.seed,{}); order=seed.get('runOrder',[]); st=read(a.state,{'version':1,'pointer':0,'completedSeasons':[],'runOrder':order}); st.setdefault('completedSeasons',[]); st.setdefault('pointer',0); st.setdefault('runOrder',order)
    if a.cmd=='reset': st.update({'pointer':0,'completedSeasons':[],'lastCompletedSeason':None,'updatedAt':now()}); write(a.state,st); print(order[0] if order else ''); return
    if a.cmd=='claim':
        if a.start_season!='auto': season=a.start_season; ptr=order.index(season) if season in order else st.get('pointer',0)
        else: ptr=int(st.get('pointer',0)); season=order[ptr] if ptr<len(order) else order[0]
        write(a.claim_file,{'claimedAt':now(),'season':season,'pointer':ptr}); print(season); return
    claim=read(a.claim_file,{}); season=claim.get('season'); ptr=int(claim.get('pointer',st.get('pointer',0)))
    if season:
        if season not in st['completedSeasons']: st['completedSeasons'].append(season)
        st['lastCompletedSeason']=season
        if a.start_season=='auto': st['pointer']=min(ptr+1,len(order))
    st['updatedAt']=now(); write(a.state,st); print(st.get('pointer',0))
if __name__=='__main__': main()

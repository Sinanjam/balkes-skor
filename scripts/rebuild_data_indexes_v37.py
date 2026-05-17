#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
TEAM_NAMES={"balıkesirspor","balikesirspor","balıkesir","balkes"}
def read_json(p:Path, default:Any)->Any:
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return default
def write_json(p:Path,obj:Any)->None:
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def season_year(s:str)->int:
    try: return int(str(s)[:4])
    except Exception: return -1
def is_balkes(name:str)->bool:
    n=(name or '').strip().lower(); return n in TEAM_NAMES or 'balıkesirspor' in n or 'balikesirspor' in n
def match_title(m:dict[str,Any])->str:
    home=m.get('homeTeam') or m.get('home') or ''; away=m.get('awayTeam') or m.get('away') or ''; score=m.get('score') or {}
    if isinstance(score,dict):
        disp=score.get('display')
        if not disp and score.get('home') is not None and score.get('away') is not None: disp=f"{score.get('home')}-{score.get('away')}"
    else: disp=str(score or '')
    return f"{home} {disp or '-'} {away}".strip() if (home or away) else str(m.get('title') or m.get('id') or 'Maç')
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--data-root',default='data'); ap.add_argument('--factory-version',default='v3.7-exact-season-repair'); args=ap.parse_args()
    root=Path(args.data_root); seasons_root=root/'seasons'; old=read_json(root/'manifest.json',{})
    season_entries=[]; search_index=[]; opponents=Counter()
    dirs=sorted([p for p in seasons_root.iterdir() if p.is_dir()] if seasons_root.exists() else [], key=lambda p:season_year(p.name), reverse=True)
    for sd in dirs:
        sid=sd.name; season_obj=read_json(sd/'season.json',{}); matches=read_json(sd/'matches_index.json',[])
        if not isinstance(matches,list): matches=[]
        if not matches and (sd/'matches').exists():
            for mp in sorted((sd/'matches').glob('*.json')):
                obj=read_json(mp,{})
                if isinstance(obj,dict): matches.append(obj)
        if not matches: continue
        competition=season_obj.get('competition') or (matches[0].get('competition','') if matches else '')
        summary=season_obj.get('summary') if isinstance(season_obj.get('summary'),dict) else {}
        entry={'id':sid,'name':season_obj.get('name') or sid,'matchCount':int(season_obj.get('matchCount') or summary.get('matches') or len(matches)),'competition':competition or '','summary':summary}
        if (sd/'standings_by_week.json').exists(): entry['standingsByWeekUrl']=f'seasons/{sid}/standings_by_week.json'
        season_entries.append(entry)
        for m in matches:
            if not isinstance(m,dict): continue
            mid=str(m.get('id') or m.get('matchId') or '')
            if not mid: continue
            search_index.append({'type':'match','season':sid,'id':mid,'title':match_title(m),'date':m.get('date') or '','url':m.get('detailUrl') or f'seasons/{sid}/matches/{mid}.json'})
            opp=''; balkes=m.get('balkes')
            if isinstance(balkes,dict): opp=str(balkes.get('opponent') or '')
            if not opp:
                home=str(m.get('homeTeam') or ''); away=str(m.get('awayTeam') or '')
                if is_balkes(home): opp=away
                elif is_balkes(away): opp=home
            if opp: opponents[opp]+=1
    now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    manifest={'app':old.get('app','Balkes Skor'),'schemaVersion':old.get('schemaVersion',3),'dataVersion':old.get('dataVersion',1),'appVersion':old.get('appVersion','0.5.0-beta-debug'),'generatedAt':now,'team':old.get('team','Balıkesirspor'),'availableSeasons':season_entries,'global':old.get('global') or {'playersIndexUrl':'players_index.json','opponentsIndexUrl':'opponents_index.json','searchIndexUrl':'search_index.json','dataReportUrl':'data_report.json'},'appDataVersion':int(time.time()),'appMinVersion':old.get('appMinVersion','0.5.0-beta-debug'),'lastUpdated':now,'dataBaseUrl':old.get('dataBaseUrl','https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/'),'factoryVersion':args.factory_version,'targetedRepairV37':True}
    report={'generatedAt':now,'sourcePolicy':'TFF-only','factoryVersion':args.factory_version,'totalAppMatches':sum(int(x.get('matchCount') or 0) for x in season_entries),'seasons':season_entries}
    write_json(root/'manifest.json',manifest); write_json(root/'data_report.json',report)
    write_json(root/'search_index.json', sorted(search_index, key=lambda x:(x.get('season',''),x.get('date',''),x.get('id',''))))
    write_json(root/'opponents_index.json',[{'name':k,'matches':v} for k,v in sorted(opponents.items())])
    if not (root/'players_index.json').exists(): write_json(root/'players_index.json',[])
    print(json.dumps({'rebuilt':True,'seasons':len(season_entries),'totalMatches':report['totalAppMatches'],'factoryVersion':args.factory_version},ensure_ascii=False,indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())

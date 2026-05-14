#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, hashlib, html, json, os, re, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime, timezone
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup=None
TFF='https://www.tff.org/Default.aspx'
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def log(x): print(f"[{datetime.now().strftime('%H:%M:%S')}] {x}", flush=True)
def read(p,d=None):
    try: return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception: return d
def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def norm(s):
    s=str(s or '').lower().strip(); s=unicodedata.normalize('NFD',s); s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    s=s.translate(str.maketrans({'ı':'i','İ':'i','ğ':'g','Ğ':'g','ü':'u','Ü':'u','ş':'s','Ş':'s','ö':'o','Ö':'o','ç':'c','Ç':'c'}))
    return re.sub(r'[^a-z0-9]+',' ',s).strip()
def balkes(s):
    n=norm(s); return 'balikesirspor' in n or 'balikesir spor' in n or 'balikesir' in n or 'balkes' in n
def url(**kw): return TFF+'?'+urllib.parse.urlencode(kw)
def text(raw):
    if BeautifulSoup:
        soup=BeautifulSoup(raw,'html.parser')
        for t in soup(['script','style','noscript']): t.decompose()
        raw=soup.get_text('\n')
    else: raw=re.sub(r'<[^>]+>','\n',raw)
    return '\n'.join(re.sub(r'\s+',' ',html.unescape(x)).strip() for x in raw.splitlines() if x.strip())
def fetch(u,p,sleep=1.5,force=False):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists() and p.stat().st_size>200 and not force: return True,p.read_text(encoding='utf-8',errors='replace')
    err=''
    for i in range(3):
        try:
            req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 BalkesTFFFactory-v2-safe','Accept-Language':'tr-TR,tr;q=0.9,en;q=0.7'})
            raw=urllib.request.urlopen(req,timeout=70).read().decode('utf-8','replace')
            p.write_text(raw,encoding='utf-8'); time.sleep(sleep); return True,raw
        except Exception as e:
            err=str(e); log(f'fetch hata {i+1}/3: {u} -> {err}'); time.sleep(max(2,sleep*(i+1)))
    p.with_suffix(p.suffix+'.error.txt').write_text(err,encoding='utf-8'); return False,''
def ids(raw,key='macId'): return sorted(set(re.findall(rf'(?:[?&]|){key}=(\d+)',raw,re.I)),key=lambda x:int(x))
def param(raw,key): return sorted(set(re.findall(rf'[?&]{re.escape(key)}=(\d+)',raw,re.I)),key=lambda x:int(x))
def balkes_ids(raw,window=1600):
    out=[]
    for m in re.finditer(r'(?:[?&]|)macId=(\d+)',raw,re.I):
        if balkes(raw[max(0,m.start()-window):min(len(raw),m.end()+window)]): out.append(m.group(1))
    return sorted(set(out),key=lambda x:int(x))
def score(s):
    m=re.search(r'\b(\d{1,2})\s*[-–]\s*(\d{1,2})\b',s)
    return (int(m.group(1)),int(m.group(2)),f"{int(m.group(1))}-{int(m.group(2))}") if m else None
def teams(tx):
    lines=[x for x in tx.splitlines() if x.strip()]
    for i,l in enumerate(lines):
        if score(l):
            b=[x for x in lines[max(0,i-6):i] if len(x)>2]; a=[x for x in lines[i+1:i+7] if len(x)>2]
            if b and a: return b[-1],a[0]
    return '',''
def mtype(*parts):
    n=norm(' '.join(str(x or '') for x in parts))
    if any(k in n for k in ['ziraat','turkiye kupasi','ztk',' kupa ']): return 'cup','Ziraat Türkiye Kupası'
    if any(k in n for k in ['play off','playoff','play offs','playoffs']): return 'playoff','Play-off'
    if any(k in n for k in ['hazirlik','friendly']): return 'friendly_or_unknown','Hazırlık/Bilinmeyen'
    return 'league','Lig'
def richness(o):
    if not isinstance(o,dict): return 0
    r=len(json.dumps(o,ensure_ascii=False))//160
    r+=len(o.get('events') or [])*10 if isinstance(o.get('events'),list) else 0
    r+=len(json.dumps(o.get('lineups') or {},ensure_ascii=False))//80 if isinstance(o.get('lineups'),dict) else 0
    r+=sum(6 for k in ['homeTeam','awayTeam','date','time','competition','week','stage'] if o.get(k))
    if isinstance(o.get('score'),dict) and o['score'].get('display'): r+=10
    return r
def should_replace(old,new): return not old or richness(new)>=richness(old)+25
def parse_detail(mid,raw,season,src,fb=None):
    fb=fb or {}; tx=text(raw); sc=score(tx); home,away=teams(tx)
    home=fb.get('homeTeam') or home; away=fb.get('awayTeam') or away
    if sc: h,a,disp=sc
    else:
        os=fb.get('score') if isinstance(fb.get('score'),dict) else {}; h,a,disp=os.get('home'),os.get('away'),os.get('display','')
    ih=balkes(home); gf=h if ih else a; ga=a if ih else h; res=''
    try: res='W' if gf>ga else 'D' if gf==ga else 'L'
    except Exception: pass
    mt,ml=mtype(fb.get('competition'),fb.get('roundType'),fb.get('stage'),tx)
    return {'id':str(mid),'season':season,'homeTeam':home,'awayTeam':away,'date':fb.get('date',''),'time':fb.get('time',''),'dateDisplay':fb.get('dateDisplay',''),'competition':fb.get('competition',''),'roundType':fb.get('roundType',''),'week':fb.get('week',''),'stage':fb.get('stage',''),'matchType':fb.get('matchType') or mt,'matchTypeLabel':fb.get('matchTypeLabel') or ml,'score':{'home':h,'away':a,'display':disp,'played':bool(disp)},'balkes':{'isHome':ih,'opponent':away if ih else home,'goalsFor':gf,'goalsAgainst':ga,'result':res},'events':[],'referees':[],'lineups':{},'rawText':tx[:20000],'quality':'B' if home and away and disp else 'D','source':{'name':'TFF','url':src,'retrievedAt':now(),'sourceType':'official_tff_match_detail'}}
def merge_old(idx,d):
    for k in ['competition','roundType','week','stage','date','time','dateDisplay','homeTeam','awayTeam','score','balkes','matchType','matchTypeLabel']:
        if isinstance(idx,dict) and idx.get(k) not in (None,'',{},[]): d[k]=idx[k]
    if not d.get('matchType'):
        d['matchType'],d['matchTypeLabel']=mtype(d.get('competition'),d.get('roundType'),d.get('stage'),d.get('rawText'))
    return d
def index(d):
    keys=['id','season','competition','roundType','week','stage','date','time','dateDisplay','homeTeam','awayTeam','matchType','matchTypeLabel','score','balkes']
    out={k:d.get(k) for k in keys if d.get(k) is not None}; out['detailUrl']=f"seasons/{d['season']}/matches/{d['id']}.json"; out['source']=d['source']; return out
def standings(raw):
    if not BeautifulSoup: return []
    soup=BeautifulSoup(raw,'html.parser'); best=[]
    for table in soup.find_all('table'):
        rows=[]
        for tr in table.find_all('tr'):
            cells=[html.unescape(c.get_text(' ',strip=True)).strip() for c in tr.find_all(['td','th'])]
            cells=[c for c in cells if c]
            if len(cells)>=4 and len(re.findall(r'\b\d+\b',' '.join(cells)))>=3: rows.append(cells)
        if len(rows)>len(best): best=rows
    out=[]
    for i,c in enumerate(best,1):
        team=next((x for x in c if not re.fullmatch(r'[\d+\-–]+',x) and len(x)>2 and 'takim' not in norm(x)), '')
        nums=[int(x) for x in re.findall(r'\b\d+\b',' '.join(c))]
        if not team or len(nums)<3: continue
        gf=nums[5] if len(nums)>5 else 0; ga=nums[6] if len(nums)>6 else 0
        out.append({'rank':nums[0] if nums else i,'team':team,'played':nums[1] if len(nums)>1 else 0,'won':nums[2] if len(nums)>2 else 0,'drawn':nums[3] if len(nums)>3 else 0,'lost':nums[4] if len(nums)>4 else 0,'goalsFor':gf,'goalsAgainst':ga,'goalDifference':gf-ga,'points':nums[-1],'isBalkes':balkes(team)})
    return out if len(out)>=4 else []
def old_index(data,season):
    arr=read(Path(data)/'seasons'/season/'matches_index.json',[])
    return {str(m['id']):m for m in arr if isinstance(m,dict) and m.get('id')} if isinstance(arr,list) else {}
def discover(item,rawroot,sleep):
    season=item['season']; selected=set(); allm=set(); tabs=[]
    for pid in item.get('pageIds',[]):
        ok,raw=fetch(url(pageID=pid),Path(rawroot)/season/'pages'/f'pageID_{pid}.html',sleep)
        if not ok: continue
        allm.update(ids(raw)); selected.update(balkes_ids(raw))
        groups=param(raw,'grupID'); weeks=param(raw,'hafta')+param(raw,'haftaID')+param(raw,'haftaNo')
        tab=standings(raw)
        if tab: tabs.append({'pageID':pid,'groupID':None,'week':None,'url':url(pageID=pid),'standings':tab})
        for gid in groups[:25]:
            gu=url(pageID=pid,grupID=gid); ok2,graw=fetch(gu,Path(rawroot)/season/'standings'/f'pageID_{pid}_group_{gid}.html',sleep)
            if not ok2: continue
            allm.update(ids(graw)); selected.update(balkes_ids(graw)); tab=standings(graw)
            if tab: tabs.append({'pageID':pid,'groupID':gid,'week':None,'url':gu,'standings':tab})
            seen=set()
            for w in sorted(set(weeks+param(graw,'hafta')+param(graw,'haftaID')+param(graw,'haftaNo')+[str(x) for x in range(1,41)]),key=lambda x:int(x)):
                wu=url(pageID=pid,grupID=gid,hafta=w); ok3,wraw=fetch(wu,Path(rawroot)/season/'standings'/f'pageID_{pid}_group_{gid}_week_{w}.html',sleep)
                if not ok3: continue
                tab=standings(wraw)
                if tab:
                    h=hashlib.sha1(json.dumps(tab,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                    if h not in seen: seen.add(h); tabs.append({'pageID':pid,'groupID':gid,'week':int(w),'url':wu,'standings':tab})
    return sorted(selected,key=lambda x:int(x)), sorted(allm,key=lambda x:int(x)), tabs
def totals(data):
    m=read(Path(data)/'manifest.json',{}); ss=m.get('availableSeasons',[]) if isinstance(m,dict) else []
    return len(ss),sum(int(s.get('matchCount') or 0) for s in ss if isinstance(s,dict))
def merge_manifest(data,counts,minS,minM):
    p=Path(data)/'manifest.json'; m=read(p,{})
    by={str(s['id']):dict(s) for s in m.get('availableSeasons',[]) if isinstance(s,dict) and s.get('id')}
    for sid,c in counts.items():
        if c>0:
            it=by.get(sid,{'id':sid,'name':sid}); it['matchCount']=c; by[sid]=it
    m['availableSeasons']=[by[k] for k in sorted(by,reverse=True)]; m['lastUpdated']=now(); m['appDataVersion']=int(m.get('appDataVersion') or 9)+1
    if len(m['availableSeasons'])<minS or sum(int(s.get('matchCount') or 0) for s in m['availableSeasons'])<minM: raise RuntimeError('publish safety stopped')
    write(p,m)
def update_report(data,minM):
    seasons=[]; total=0
    for p in sorted((Path(data)/'seasons').glob('*/matches_index.json'),reverse=True):
        arr=read(p,[]); cnt=len(arr) if isinstance(arr,list) else 0; total+=cnt; seasons.append({'id':p.parent.name,'matchCount':cnt})
    if total<minM: raise RuntimeError('report safety stopped')
    r=read(Path(data)/'data_report.json',{}) or {}; r.update({'generatedAt':now(),'sourcePolicy':'TFF-only','factoryVersion':'v2-safe','totalAppMatches':total,'seasons':seasons}); write(Path(data)/'data_report.json',r)
def process(item,args):
    season=item['season']; data=Path(args.data_root); raw=Path(args.raw_root); rep=Path(args.reports_root)
    log(f'=== {season} başladı ===')
    old=old_index(data,season); sel,allids,tabs=discover(item,raw,args.sleep)
    queue=set(old)|set(map(str,item.get('knownMatchIds',[])))|set(sel)
    log(f'{season}: selectedIds={len(sel)}, allDiscoveredIds={len(allids)}, existingIds={len(old)}, finalQueue={len(queue)}, standingsCandidates={len(tabs)}')
    sdir=data/'seasons'/season; mdir=sdir/'matches'; mdir.mkdir(parents=True,exist_ok=True)
    pub={}; kept=repl=created=0
    for mid in sorted(queue,key=lambda x:int(x)):
        fb=old.get(mid,{}) ; new=None
        for u in [url(macId=mid,pageID=528), url(pageID=29,macId=mid)]:
            ok,rawh=fetch(u,raw/season/'matches'/f'{mid}.html',args.sleep,args.force)
            if ok and (balkes(text(rawh)) or fb): new=merge_old(fb,parse_detail(mid,rawh,season,u,fb)); break
        dp=mdir/f'{mid}.json'; ex=read(dp,{})
        if new and should_replace(ex,new): write(dp,new); pub[mid]=index(new); repl+=1 if ex else 0; created+=0 if ex else 1
        elif ex: kept+=1; pub[mid]=index(merge_old(fb,ex)) if isinstance(ex,dict) and ex.get('source') else fb
        elif fb: pub[mid]=fb
    for mid,m in old.items(): pub.setdefault(mid,m)
    arr=sorted(pub.values(),key=lambda m:(str(m.get('date') or ''),int(str(m.get('id') or 0))))
    write(sdir/'matches_index.json',arr)
    chosen=[]
    for c in tabs:
        if any(r.get('isBalkes') for r in c.get('standings',[])): chosen.append({'week':c.get('week') or len(chosen)+1,'source':{'name':'TFF','url':c['url'],'retrievedAt':now(),'sourceType':'official_tff_standings'},'pageID':c.get('pageID'),'groupID':c.get('groupID'),'standings':c['standings']})
    if chosen:
        uniq={hashlib.sha1(json.dumps(x['standings'],ensure_ascii=False,sort_keys=True).encode()).hexdigest():x for x in chosen}; write(sdir/'standings_by_week.json',sorted(uniq.values(),key=lambda x:int(x['week'])))
    elif not (sdir/'standings_by_week.json').exists(): write(sdir/'standings_by_week.json',[])
    types={}
    for m in arr: types[m.get('matchType') or 'league']=types.get(m.get('matchType') or 'league',0)+1
    sj=read(sdir/'season.json',{}) or {}; sj.update({'id':season,'name':season,'factoryVersion':'v2-safe','sourcePolicy':'TFF-only','updatedAt':now(),'summary':{'matches':len(arr),'matchTypes':types},'files':{'matchesIndex':f'seasons/{season}/matches_index.json','standingsByWeek':f'seasons/{season}/standings_by_week.json'}}); write(sdir/'season.json',sj)
    q={'season':season,'selectedIds':len(sel),'allDiscoveredIds':len(allids),'existingIds':len(old),'finalQueue':len(queue),'matchesPublished':len(arr),'detailFiles':len(list(mdir.glob('*.json'))),'detailsCreated':created,'detailsReplaced':repl,'detailsKeptBecauseExistingWasRicher':kept,'standingsSnapshots':len(read(sdir/'standings_by_week.json',[])),'balkesTableFound':bool(chosen),'matchTypeCounts':types,'generatedAt':now()}
    write(rep/'seasons'/f'{season}_quality.json',q); return q
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--seed',default='sources/tff/registry/balkes_tff_seed_registry.json'); ap.add_argument('--data-root',default='data'); ap.add_argument('--raw-root',default='sources/tff/raw'); ap.add_argument('--reports-root',default='reports/tff_factory'); ap.add_argument('--start-season',default='2025-2026'); ap.add_argument('--max-seasons',type=int,default=1); ap.add_argument('--sleep',type=float,default=1.5); ap.add_argument('--force',action='store_true')
    a=ap.parse_args(); seed=read(a.seed,{}); minS=int(seed.get('baseline',{}).get('minSeasons',12)); minM=int(seed.get('baseline',{}).get('minMatches',177))
    before=totals(a.data_root); log(f'before={before}, required>={minS}/{minM}')
    by={s['season']:s for s in seed.get('seasons',[]) if isinstance(s,dict) and s.get('season')}; q=[]; seen=False
    for sid in seed.get('runOrder',[]):
        if sid==a.start_season: seen=True
        if seen and sid in by: q.append(by[sid])
    q=q[:a.max_seasons]; log('queue='+', '.join(x['season'] for x in q))
    proc=[]; counts={}
    for it in q: res=process(it,a); proc.append(res); counts[it['season']]=res['matchesPublished']
    merge_manifest(a.data_root,counts,minS,minM); update_report(a.data_root,minM); after=totals(a.data_root)
    write(Path(a.reports_root)/'tff_factory_summary.json',{'generatedAt':now(),'status':'ok','sourcePolicy':'TFF-only','factoryVersion':'v2-safe','startSeason':a.start_season,'processed':proc,'before':{'seasons':before[0],'matches':before[1]},'after':{'seasons':after[0],'matches':after[1]},'safeToPush':True,'notes':['v2-safe mevcut zengin maç detaylarını daha zayıf parse ile ezmez.','Raw HTML artifact olarak saklanır, repo commit edilmez.','Lig/ZTK/Play-off matchType alanıyla sınıflandırılır.']})
    log(f'DONE safeToPush=True after={after}')
if __name__=='__main__': main()

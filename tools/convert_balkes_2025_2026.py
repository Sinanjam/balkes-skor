#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Balıkesirspor 2025-2026 TFF tarama çıktısını Balkes Skor uygulamasının okuyacağı
GitHub/raw JSON veri yapısına dönüştürür. Sadece açık TFF HTML çıktıları kullanılır.
"""
import json, re, hashlib, shutil, os, zipfile
from pathlib import Path
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from PIL import Image

IN_ROOT = Path('/mnt/data/balkes_zip_in/balkes-tff-2025-2026')
RAW = IN_ROOT / 'raw_html_2025_2026'
PROC = IN_ROOT / 'processed'
OUT = Path('/mnt/data/balkes-skor-2025-2026-app-data')
DATA = OUT / 'data'
SEASON_DIR = DATA / 'seasons' / '2025-2026'
MATCHES_DIR = SEASON_DIR / 'matches'
ASSETS = OUT / 'assets'
LOGO_SRC = Path('/mnt/data/sporty_red_and_white_logo_design.png')
if not LOGO_SRC.exists():
    LOGO_SRC = Path('/mnt/data/imagegen.png')

TEAM_ID = 'balikesirspor'
TEAM_NAMES = ['BALIKESİRSPOR', 'NEV SAĞLIK GRUBU BALIKESİRSPOR']
SEASON='2025-2026'
LEAGUE='Nesine 3. Lig'
GROUP='04. Grup'
BASE_TFF='https://www.tff.org/Default.aspx'

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def clean(s):
    return re.sub(r'\s+', ' ', (s or '').replace('\xa0',' ')).strip()

def norm_team(s):
    s=clean(s)
    if s in TEAM_NAMES:
        return 'Balıkesirspor'
    if s == 'ÜLKEA NAZİLLİSPOR':
        return 'Nazilli Spor A.Ş.'
    return s

def raw_team(s):
    return clean(s)

def is_balkes(s):
    u=clean(s).upper()
    return any(n in u for n in TEAM_NAMES)

def full_url(href):
    if not href:
        return None
    href = href.replace('&amp;', '&')
    if href.startswith('http'):
        return href
    if href.startswith('/'):
        return 'https://www.tff.org' + href
    return 'https://www.tff.org/' + href

def parse_score(score):
    score=clean(score)
    m=re.search(r'(\d+)\s*-\s*(\d+)', score)
    if not m:
        return {'home': None, 'away': None, 'display': score, 'played': False}
    return {'home': int(m.group(1)), 'away': int(m.group(2)), 'display': score, 'played': True}

def parse_date(date_txt):
    """Return ISO-ish date/time fields. Supports 07.09.2025 17:00 and 24 Nisan 2026 20:00."""
    txt=clean(date_txt)
    months={'Ocak':'01','Şubat':'02','Mart':'03','Nisan':'04','Mayıs':'05','Haziran':'06','Temmuz':'07','Ağustos':'08','Eylül':'09','Ekim':'10','Kasım':'11','Aralık':'12'}
    m=re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}:\d{2})', txt)
    if m:
        d,mo,y,t=m.groups()
        return {'date': f'{y}-{int(mo):02d}-{int(d):02d}', 'time': t, 'display': txt}
    m=re.match(r'(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})\s+(\d{1,2}:\d{2})', txt)
    if m:
        d,mon,y,t=m.groups()
        mo=months.get(mon)
        if mo:
            return {'date': f'{y}-{mo}-{int(d):02d}', 'time': t, 'display': txt}
    return {'date': None, 'time': None, 'display': txt}

def minute_num(t):
    t=clean(t).replace('.dk','').replace('dk','')
    if t in ('MS','İY'):
        return None
    m=re.search(r'(\d+)(?:\+(\d+))?', t)
    if not m: return None
    return int(m.group(1)) + (int(m.group(2))/100 if m.group(2) else 0)

def id_suffix(soup, suffix):
    return soup.find(id=lambda x: x and x.endswith(suffix))

def text_suffix(soup, suffix):
    tag=id_suffix(soup,suffix)
    return clean(tag.get_text(' ', strip=True)) if tag else None

def get_control_items(soup, team_no, rpt, label_suffix, extra_suffix=None, img_suffix=None):
    prefix=f'grdTakim{team_no}_{rpt}_'
    items=[]
    # collect control numbers by any matching id
    nums=set()
    for tag in soup.find_all(id=lambda x: x and prefix in x):
        m=re.search(r'_ctl(\d+)_', tag.get('id',''))
        if m and m.group(1)!='00':
            nums.add(m.group(1))
    for n in sorted(nums, key=int):
        label=soup.find(id=lambda x: x and f'{prefix}ctl{n}_{label_suffix}' in x)
        if not label: continue
        obj={'name': clean(label.get_text(' ',strip=True))}
        if extra_suffix:
            extra=soup.find(id=lambda x: x and f'{prefix}ctl{n}_{extra_suffix}' in x)
            if extra:
                obj['minute_text']=clean(extra.get_text(' ',strip=True))
                obj['minute']=minute_num(obj['minute_text'])
        if img_suffix:
            img=soup.find(id=lambda x: x and f'{prefix}ctl{n}_{img_suffix}' in x)
            if img:
                alt=clean(img.get('alt') or '')
                if alt:
                    obj['card_type_tr']=alt
                    obj['type']='yellow_card' if 'Sarı' in alt else ('red_card' if 'Kırmızı' in alt else 'card')
        href=label.get('href') if hasattr(label, 'get') else None
        if href:
            obj['person_url']=full_url(href)
            km=re.search(r'kisiId=(\d+)', href, re.I)
            if km: obj['tff_person_id']=km.group(1)
        items.append(obj)
    return items

def get_players(soup, team_no, rpt):
    prefix=f'grdTakim{team_no}_{rpt}_'
    nums=set()
    for tag in soup.find_all(id=lambda x: x and prefix in x and ('_formaNo' in x or '_lnkOyuncu' in x)):
        m=re.search(r'_ctl(\d+)_', tag.get('id',''))
        if m and m.group(1)!='00': nums.add(m.group(1))
    players=[]
    for n in sorted(nums, key=int):
        no=soup.find(id=lambda x: x and f'{prefix}ctl{n}_formaNo' in x)
        a=soup.find(id=lambda x: x and f'{prefix}ctl{n}_lnkOyuncu' in x)
        if not a: continue
        obj={'shirt_no': clean(no.get_text(' ',strip=True)) if no else None, 'name': clean(a.get_text(' ',strip=True))}
        href=a.get('href')
        if href:
            obj['person_url']=full_url(href)
            km=re.search(r'kisiId=(\d+)', href, re.I)
            if km: obj['tff_person_id']=km.group(1)
        players.append(obj)
    return players

def parse_goal_text(txt):
    txt=clean(txt)
    # examples: BERHAN DENİZ,71.dk (F), NAME,45+2.dk (P)
    m=re.match(r'(.+?),\s*([^,]+?)(?:\s+\(([^)]+)\))?$', txt)
    if m:
        return {'name': clean(m.group(1)), 'minute_text': clean(m.group(2)), 'minute': minute_num(m.group(2)), 'goal_kind': m.group(3) or None, 'raw': txt}
    return {'name': txt, 'minute_text': None, 'minute': None, 'goal_kind': None, 'raw': txt}

def parse_match_page(path, fallback_id=None):
    soup=BeautifulSoup(path.read_text(encoding='utf-8', errors='replace'), 'html.parser')
    home=clean(text_suffix(soup, '_lnkTakim1'))
    away=clean(text_suffix(soup, '_lnkTakim2'))
    if not home or not away:
        # fallback on title
        title=clean(soup.title.get_text(' ',strip=True) if soup.title else '')
    home_score=text_suffix(soup, '_lblTakim1Skor')
    away_score=text_suffix(soup, '_lblTakim2Skor') or text_suffix(soup, '_Label12')
    org=text_suffix(soup, '_lblOrganizasyonAdi')
    code=text_suffix(soup, '_lblKod')
    venue=text_suffix(soup, '_lnkStad')
    tarih=text_suffix(soup, '_lblTarih')
    dt=parse_date(tarih or '')
    refs=[]
    for a in soup.find_all(id=lambda x: x and 'dtMacBilgisi_rpt_' in x and x.endswith('_lnkHakem')):
        txt=clean(a.get_text(' ',strip=True))
        role=None; name=txt
        m=re.match(r'(.+?)\((.+?)\)$', txt)
        if m:
            name=clean(m.group(1)); role=clean(m.group(2))
        obj={'name':name, 'role_tr':role, 'raw':txt}
        href=a.get('href')
        if href:
            obj['person_url']=full_url(href)
            km=re.search(r'kisiId=(\d+)', href, re.I)
            if km: obj['tff_person_id']=km.group(1)
        refs.append(obj)
    teams={}
    events=[]
    for team_no, side in [(1,'home'),(2,'away')]:
        team_name = home if team_no==1 else away
        starting=get_players(soup, team_no, 'rptKadrolar')
        bench=get_players(soup, team_no, 'rptYedekler')
        coaches=get_control_items(soup, team_no, 'rptTeknikKadro', 'lnkTeknikSorumlu')
        goals=[]
        for g in get_control_items(soup, team_no, 'rptGoller', 'lblGol'):
            pg=parse_goal_text(g['name'])
            pg.update({'team': norm_team(team_name), 'side': side, 'type':'goal'})
            goals.append(pg)
            events.append({'type':'goal','team':norm_team(team_name),'side':side,'player':pg['name'],'minute':pg['minute'],'minute_text':pg['minute_text'],'goal_kind':pg.get('goal_kind'), 'raw': pg['raw']})
        cards=[]
        for c in get_control_items(soup, team_no, 'rptKartlar', 'lblKart', 'd', 'k'):
            cards.append(c)
            events.append({'type':c.get('type','card'), 'team':norm_team(team_name), 'side':side, 'player':c['name'], 'minute':c.get('minute'), 'minute_text':c.get('minute_text'), 'card_type_tr':c.get('card_type_tr')})
        outs=get_control_items(soup, team_no, 'rptCikanlar', 'lblCikan', 'oc')
        ins=get_control_items(soup, team_no, 'rptGirenler', 'lblGiren', 'og')
        # pair substitutions by order + same minute if possible
        subs=[]
        for idx, (outp, inp) in enumerate(zip(outs, ins), start=1):
            minute_text=inp.get('minute_text') or outp.get('minute_text')
            sub={'minute_text':minute_text, 'minute':minute_num(minute_text or ''), 'player_in':inp.get('name'), 'player_out':outp.get('name')}
            subs.append(sub)
            events.append({'type':'substitution','team':norm_team(team_name),'side':side,'minute':sub['minute'],'minute_text':minute_text,'player_in':sub['player_in'],'player_out':sub['player_out']})
        teams[side]={'team':norm_team(team_name),'team_raw':team_name,'starting11':starting,'substitutes':bench,'coach':coaches[0]['name'] if coaches else None,'coaches':coaches,'goals':goals,'cards':cards,'substitutions':subs,'players_out':outs,'players_in':ins}
    events.sort(key=lambda e: (999 if e.get('minute') is None else e.get('minute'), e.get('type','')))
    mid=fallback_id
    mm=re.search(r'macId-(\d+)', path.name)
    if mm: mid=mm.group(1)
    if not mid:
        m=re.search(r'macId=(\d+)', str(path)); mid=m.group(1) if m else None
    return {
        'id': mid,
        'tff_match_id': mid,
        'season': SEASON,
        'competition': org or LEAGUE,
        'match_code': code,
        'homeTeam': norm_team(home),
        'awayTeam': norm_team(away),
        'homeTeamRaw': home,
        'awayTeamRaw': away,
        'score': {'home': int(home_score) if (home_score or '').isdigit() else None, 'away': int(away_score) if (away_score or '').isdigit() else None, 'display': f'{home_score}-{away_score}' if home_score and away_score else None, 'played': bool(home_score and away_score)},
        'date': dt['date'], 'time': dt['time'], 'dateDisplay': dt['display'],
        'venue': venue,
        'referees': refs,
        'lineups': {'home': teams.get('home',{}), 'away': teams.get('away',{})},
        'events': events,
        'source': {'name':'TFF','url':f'https://www.tff.org/Default.aspx?pageID=29&macId={mid}' if mid else None},
        'source_file': path.name,
    }

def parse_fixtures_from_week_pages():
    fixtures={}
    playoff_stage=None
    for path in sorted(RAW.glob('Default.aspx_grupID-2786_hafta-*_pageID-971_*.html')):
        wm=re.search(r'hafta-(\d+)_', path.name)
        page_week=int(wm.group(1)) if wm else None
        soup=BeautifulSoup(path.read_text(encoding='utf-8', errors='replace'), 'html.parser')
        for tr in soup.find_all('tr'):
            cells=[clean(td.get_text(' ',strip=True)) for td in tr.find_all(['td','th'], recursive=False)]
            if len(cells)==1 and re.search(r'(Final|\d+\.Tur) Maçları', cells[0]):
                sm=re.search(r'(Final|\d+\.Tur) Maçları', cells[0])
                playoff_stage=(sm.group(1)+' Maçları') if sm else cells[0]
            links=tr.find_all('a', href=re.compile(r'macId=', re.I))
            if not links: continue
            # Direct date rows from selected week / playoff table
            if len(cells)>=5 and (re.match(r'\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2}', cells[0]) or re.match(r'\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4}\s+\d{1,2}:\d{2}', cells[0])):
                date_txt, home, score_txt, away = cells[0], cells[1], cells[2], cells[3]
            elif len(cells)==3:
                # all-season fixture list has no date; only use if needed, but details will supply date
                date_txt, home, score_txt, away = None, cells[0], cells[1], cells[2]
            else:
                continue
            if not (is_balkes(home) or is_balkes(away)): continue
            href=None; mid=None
            for a in links:
                h=a.get('href') or ''
                m=re.search(r'macId=(\d+)', h, re.I)
                if m:
                    mid=m.group(1); href=h; break
            if not mid: continue
            score=parse_score(score_txt)
            # prefer rows with date over no-date rows
            if mid in fixtures and fixtures[mid].get('dateDisplay'):
                continue
            dt=parse_date(date_txt or '')
            kind='playoff' if date_txt and not re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', date_txt) else 'league'
            fixtures[mid]={
                'id':mid,'tff_match_id':mid,'season':SEASON,'competition':LEAGUE,
                'group': GROUP if kind=='league' else None,
                'roundType':kind,
                'week': page_week if kind=='league' and page_week and page_week<=30 else None,
                'stage': playoff_stage if kind=='playoff' else (f'{page_week}. Hafta' if page_week and page_week<=30 else None),
                'date':dt['date'],'time':dt['time'],'dateDisplay':dt['display'] if date_txt else None,
                'homeTeam':norm_team(home),'awayTeam':norm_team(away),'homeTeamRaw':home,'awayTeamRaw':away,
                'score':score,
                'source':{'name':'TFF','url':full_url(href)},
                'sourceWeekPage':f'https://www.tff.org/Default.aspx?grupID=2786&hafta={page_week}&pageID=971' if page_week else None,
            }
    return fixtures

def parse_standings():
    snapshots=[]
    for wk in range(1,31):
        paths=list(RAW.glob(f'Default.aspx_grupID-2786_hafta-{wk}_pageID-971_*.html'))
        if not paths: continue
        soup=BeautifulSoup(paths[0].read_text(encoding='utf-8', errors='replace'), 'html.parser')
        table=None
        for tb in soup.find_all('table'):
            txt=clean(tb.get_text(' ',strip=True))
            if 'Sezonu Puan Cetveli' in txt and ' O G B M A Y AV P ' in f' {txt} ':
                table=tb; break
        if not table: continue
        rows=[]
        for tr in table.find_all('tr'):
            cells=[clean(td.get_text(' ',strip=True)) for td in tr.find_all(['td','th'], recursive=False)]
            if len(cells)==9 and re.match(r'\d+\.', cells[0]):
                m=re.match(r'(\d+)\.\s*(.+)', cells[0])
                rank=int(m.group(1)); team=m.group(2)
                vals=[]
                for v in cells[1:]:
                    try: vals.append(int(v))
                    except: vals.append(None)
                rows.append({'rank':rank,'team':norm_team(team),'teamRaw':team,'played':vals[0],'won':vals[1],'drawn':vals[2],'lost':vals[3],'goalsFor':vals[4],'goalsAgainst':vals[5],'goalDifference':vals[6],'points':vals[7],'isBalkes':is_balkes(team)})
        if rows:
            snapshots.append({'season':SEASON,'competition':LEAGUE,'group':GROUP,'week':wk,'standings':rows,'balkes':next((r for r in rows if r['isBalkes']), None),'source':{'name':'TFF','url':f'https://www.tff.org/Default.aspx?grupID=2786&hafta={wk}&pageID=971'}})
    return snapshots

def create_logo_assets():
    ASSETS.mkdir(parents=True, exist_ok=True)
    if not LOGO_SRC.exists(): return []
    img=Image.open(LOGO_SRC).convert('RGBA')
    copied=[]
    # app source logo
    shutil.copy(LOGO_SRC, ASSETS/'logo_balkes_skor_source.png')
    copied.append(str(ASSETS/'logo_balkes_skor_source.png'))
    sizes={'mipmap-mdpi':48,'mipmap-hdpi':72,'mipmap-xhdpi':96,'mipmap-xxhdpi':144,'mipmap-xxxhdpi':192}
    for folder, size in sizes.items():
        d=ASSETS/'android_res'/folder
        d.mkdir(parents=True, exist_ok=True)
        icon=img.resize((size,size), Image.LANCZOS)
        icon.save(d/'ic_launcher.png')
        icon.save(d/'ic_launcher_round.png')
        copied += [str(d/'ic_launcher.png'), str(d/'ic_launcher_round.png')]
    return copied

def sha256_file(p):
    h=hashlib.sha256();
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(65536), b''):
            h.update(b)
    return h.hexdigest()

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    fixtures=parse_fixtures_from_week_pages()
    standings=parse_standings()
    # detail pages: only parse fixture match ids if pageID-29 exists
    details={}
    for mid in sorted(fixtures.keys(), key=lambda x:int(x)):
        paths=sorted(RAW.glob(f'Default.aspx_macId-{mid}_pageID-29_*.html'))
        if paths:
            try:
                details[mid]=parse_match_page(paths[0], mid)
            except Exception as e:
                details[mid]={'id':mid,'parse_error':str(e)}
    # merge fixture with detail
    matches=[]
    for mid, fx in fixtures.items():
        d=details.get(mid, {})
        merged={**fx}
        # detail is richer, but keep fixture week/stage
        for k,v in d.items():
            if v not in (None, '', [], {}):
                merged[k]=v
        merged['week']=fx.get('week')
        merged['stage']=fx.get('stage')
        merged['roundType']=fx.get('roundType')
        merged['sourceWeekPage']=fx.get('sourceWeekPage')
        # calculate balkes perspective
        is_home=is_balkes(merged.get('homeTeamRaw') or merged.get('homeTeam'))
        sc=merged.get('score') or {}
        gf=sc.get('home') if is_home else sc.get('away')
        ga=sc.get('away') if is_home else sc.get('home')
        result=None
        if isinstance(gf,int) and isinstance(ga,int): result='W' if gf>ga else ('D' if gf==ga else 'L')
        merged['balkes']={'isHome':is_home,'opponent':merged.get('awayTeam') if is_home else merged.get('homeTeam'), 'goalsFor':gf,'goalsAgainst':ga,'result':result}
        matches.append(merged)
    # Sort by date, then league week/playoff date
    matches.sort(key=lambda m: (m.get('date') or '9999-99-99', m.get('time') or '99:99', int(m.get('id') or 0)))
    # Write individual details and index (without huge nested? keep all? index slim)
    index=[]
    for m in matches:
        mid=m['id']
        out=MATCHES_DIR/f'{mid}.json'
        with out.open('w',encoding='utf-8') as f: json.dump(m,f,ensure_ascii=False,indent=2)
        index.append({
            'id':mid,'season':SEASON,'competition':m.get('competition') or LEAGUE,'roundType':m.get('roundType'),'week':m.get('week'),'stage':m.get('stage'),'date':m.get('date'),'time':m.get('time'),'dateDisplay':m.get('dateDisplay'),
            'homeTeam':m.get('homeTeam'),'awayTeam':m.get('awayTeam'),'score':m.get('score'),'balkes':m.get('balkes'),
            'detailUrl':f'seasons/2025-2026/matches/{mid}.json','source':m.get('source')
        })
    # season summary
    league_matches=[m for m in matches if m.get('roundType')=='league']
    playoff_matches=[m for m in matches if m.get('roundType')=='playoff']
    wins=sum(1 for m in league_matches if m['balkes']['result']=='W')
    draws=sum(1 for m in league_matches if m['balkes']['result']=='D')
    losses=sum(1 for m in league_matches if m['balkes']['result']=='L')
    gf=sum((m['balkes'].get('goalsFor') or 0) for m in league_matches if isinstance(m['balkes'].get('goalsFor'), int))
    ga=sum((m['balkes'].get('goalsAgainst') or 0) for m in league_matches if isinstance(m['balkes'].get('goalsAgainst'), int))
    final_standing=standings[-1]['balkes'] if standings and standings[-1].get('balkes') else None
    season_json={
        'id':SEASON,'name':SEASON,'team':{'id':TEAM_ID,'name':'Balıkesirspor','tffClubId':'135'},'competition':LEAGUE,'group':GROUP,
        'summary':{'leagueMatches':len(league_matches),'playoffMatches':len(playoff_matches),'wins':wins,'draws':draws,'losses':losses,'goalsFor':gf,'goalsAgainst':ga,'goalDifference':gf-ga,'points':final_standing.get('points') if final_standing else None,'finalRank':final_standing.get('rank') if final_standing else None},
        'files':{'matchesIndex':'seasons/2025-2026/matches_index.json','standingsByWeek':'seasons/2025-2026/standings_by_week.json'},
        'source':{'name':'TFF','fixtureUrl':'https://www.tff.org/Default.aspx?grupID=2786&pageID=971'},
    }
    SEASON_DIR.mkdir(parents=True, exist_ok=True)
    (SEASON_DIR/'matches_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
    (SEASON_DIR/'standings_by_week.json').write_text(json.dumps(standings,ensure_ascii=False,indent=2),encoding='utf-8')
    (SEASON_DIR/'season.json').write_text(json.dumps(season_json,ensure_ascii=False,indent=2),encoding='utf-8')
    # search index
    search=[]
    for item in index:
        search.append({'type':'match','id':item['id'],'season':SEASON,'title':f"{item['homeTeam']} - {item['awayTeam']}",'subtitle':f"{item.get('dateDisplay') or item.get('date') or ''} · {item.get('score',{}).get('display') or ''}",'url':item['detailUrl'],'tokens':[item['homeTeam'],item['awayTeam'],item['id'],item.get('stage') or '']})
    (DATA/'search_index.json').write_text(json.dumps(search,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={'app':'Balkes Skor','schemaVersion':1,'generatedAt':now_iso(),'dataBaseUrl':'https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/','team':{'id':TEAM_ID,'name':'Balıkesirspor'},'assets':{'logo':'assets/logo_balkes_skor_source.png'},'availableSeasons':[{'id':SEASON,'name':SEASON,'competition':LEAGUE,'group':GROUP,'seasonUrl':'seasons/2025-2026/season.json','matchesIndexUrl':'seasons/2025-2026/matches_index.json','standingsUrl':'seasons/2025-2026/standings_by_week.json'}]}
    (DATA/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    create_logo_assets()
    # copy converter script and original summary outputs
    tools=OUT/'tools'; tools.mkdir(parents=True, exist_ok=True)
    shutil.copy(Path(__file__), tools/'convert_balkes_2025_2026.py')
    raw_report = IN_ROOT/'RAPOR_2025_2026.md'
    if raw_report.exists(): shutil.copy(raw_report, OUT/'TFF_TARAMA_ORIJINAL_RAPOR.md')
    # report
    events_count=sum(len(m.get('events',[])) for m in matches)
    lineups_complete=sum(1 for m in matches if len(m.get('lineups',{}).get('home',{}).get('starting11',[]))>=11 and len(m.get('lineups',{}).get('away',{}).get('starting11',[]))>=11)
    cards_count=sum(1 for m in matches for e in m.get('events',[]) if 'card' in e.get('type',''))
    goals_count=sum(1 for m in matches for e in m.get('events',[]) if e.get('type')=='goal')
    subs_count=sum(1 for m in matches for e in m.get('events',[]) if e.get('type')=='substitution')
    report=f"""# Balkes Skor 2025-2026 Veri Dönüştürme Raporu

## Kaynak
- Kaynak zip: `balkes-tff-2025-2026.zip`
- Kaynak türü: TFF açık HTML sayfaları
- Sezon: {SEASON}
- Lig/grup: {LEAGUE} / {GROUP}
- Dönüştürme zamanı: {now_iso()}

## Üretilen uygulama veri yapısı
- `data/manifest.json`
- `data/search_index.json`
- `data/seasons/2025-2026/season.json`
- `data/seasons/2025-2026/matches_index.json`
- `data/seasons/2025-2026/standings_by_week.json`
- `data/seasons/2025-2026/matches/*.json`
- `assets/logo_balkes_skor_source.png`
- `assets/android_res/mipmap-*/ic_launcher.png`

## Sayısal özet
- Uygulamaya alınan Balıkesirspor maçı: **{len(matches)}**
- Lig maçı: **{len(league_matches)}**
- Play-off maçı: **{len(playoff_matches)}**
- Haftalık puan durumu snapshot: **{len(standings)}**
- Detay sayfasından ilk 11’i iki takım için de çıkan maç: **{lineups_complete}/{len(matches)}**
- Olay kaydı toplamı: **{events_count}**
- Gol olayı: **{goals_count}**
- Kart olayı: **{cards_count}**
- Oyuncu değişikliği olayı: **{subs_count}**

## Balıkesirspor lig özeti
- Oynanan: **{len(league_matches)}**
- Galibiyet/Beraberlik/Mağlubiyet: **{wins}/{draws}/{losses}**
- Gol: **{gf}-{ga}**
- Averaj: **{gf-ga}**
- Son puan durumu satırı: **{final_standing.get('rank') if final_standing else '?'}. sıra, {final_standing.get('points') if final_standing else '?'} puan**

## Notlar
- Logo/resim veri taramasından çekilmedi; uygulama logosu olarak bu konuşmada üretilen **Balkes Skor** logosu eklendi.
- TFF HTML içindeki kulüp logo bağlantıları uygulama verisine indirilmiş görsel olarak alınmadı.
- `raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/` tabanına göre manifest hazırlandı.
- GitHub Actions dosyası eklenmedi.
- Uygulama içinde maç listesi için `matches_index.json`, maç detayı için `matches/{{macId}}.json`, puan durumu için `standings_by_week.json` okunmalı.
"""
    (OUT/'RAPOR.md').write_text(report,encoding='utf-8')
    # checksums
    checks=[]
    for p in sorted(OUT.rglob('*')):
        if p.is_file():
            checks.append({'path':str(p.relative_to(OUT)), 'bytes':p.stat().st_size, 'sha256':sha256_file(p)})
    (OUT/'CHECKSUMS.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    # zip
    zip_path=Path('/mnt/data/balkes-skor-2025-2026-app-data.zip')
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file(): z.write(p, p.relative_to(OUT.parent))
    print('OUT',OUT)
    print('ZIP',zip_path, zip_path.stat().st_size)
    print(report)

if __name__=='__main__':
    main()

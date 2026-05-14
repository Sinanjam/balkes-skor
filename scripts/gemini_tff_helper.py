#!/usr/bin/env python3
import argparse,json,os,re,time,urllib.request
from pathlib import Path
from datetime import datetime,timezone
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def write(p,o): p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def strip(raw): raw=re.sub(r'<script.*?</script>',' ',raw,flags=re.I|re.S); raw=re.sub(r'<style.*?</style>',' ',raw,flags=re.I|re.S); raw=re.sub(r'<[^>]+>','\n',raw); return '\n'.join(re.sub(r'\s+',' ',x).strip() for x in raw.splitlines() if x.strip())[:7000]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--reports-root',default='reports/tff_factory'); ap.add_argument('--raw-root',default='sources/tff/raw'); ap.add_argument('--max-files',type=int,default=2); ap.add_argument('--sleep',type=float,default=5.0); ap.add_argument('--model',default=os.environ.get('GEMINI_MODEL','gemini-2.0-flash')); a=ap.parse_args(); out=Path(a.reports_root)/'gemini_diagnostics'; out.mkdir(parents=True,exist_ok=True)
    key=os.environ.get('GEMINI_API_KEY')
    if not key: write(out/'gemini_skipped.json',{'generatedAt':now(),'status':'skipped','reason':'GEMINI_API_KEY yok'}); print('Gemini skipped'); return
    results=[]
    for f in sorted(Path(a.raw_root).glob('**/*.html'))[:a.max_files]:
        prompt=json.dumps({'task':'TFF HTML için parser diagnostic üret. Veri kaynağı sadece TFF. Uygulama verisi üretme.','file':str(f),'schema':{'containsBalikesirspor':'boolean','parserProblem':'string','suggestedParserRule':'string','confidence':'high|medium|low'},'text':strip(f.read_text(encoding='utf-8',errors='replace')[:50000])},ensure_ascii=False)
        try:
            body=json.dumps({'contents':[{'role':'user','parts':[{'text':prompt}]}],'generationConfig':{'temperature':0.1,'responseMimeType':'application/json'}}).encode()
            req=urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{a.model}:generateContent?key={key}',data=body,headers={'Content-Type':'application/json'})
            resp=json.loads(urllib.request.urlopen(req,timeout=90).read().decode('utf-8','replace'))
            txt=resp['candidates'][0]['content']['parts'][0]['text']; results.append(json.loads(txt))
        except Exception as e: results.append({'file':str(f),'error':str(e)})
        time.sleep(a.sleep)
    write(out/'gemini_summary.json',{'generatedAt':now(),'status':'ok','model':a.model,'filesAnalyzed':len(results),'results':results}); print('Gemini diagnostics written')
if __name__=='__main__': main()

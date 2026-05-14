#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, json, os, re, time, urllib.request
from pathlib import Path
from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def write(path,obj):
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
def strip_html(raw):
    raw=re.sub(r"<script.*?</script>"," ",raw,flags=re.I|re.S)
    raw=re.sub(r"<style.*?</style>"," ",raw,flags=re.I|re.S)
    raw=re.sub(r"<[^>]+>","\n",raw)
    return "\n".join(re.sub(r"\s+"," ",x).strip() for x in raw.splitlines() if x.strip())[:8000]
def call(key,model,prompt):
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body=json.dumps({"contents":[{"role":"user","parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.1,"responseMimeType":"application/json"}}).encode()
    req=urllib.request.Request(url,data=body,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=90) as res:
        return json.loads(res.read().decode("utf-8","replace"))
def response_text(resp):
    try: return resp["candidates"][0]["content"]["parts"][0]["text"]
    except Exception: return json.dumps(resp, ensure_ascii=False)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reports-root", default="reports/tff_factory")
    ap.add_argument("--raw-root", default="sources/tff/raw")
    ap.add_argument("--model", default=os.environ.get("GEMINI_MODEL","gemini-2.0-flash"))
    ap.add_argument("--max-files", type=int, default=3)
    ap.add_argument("--sleep", type=float, default=6)
    args=ap.parse_args()
    out=Path(args.reports_root)/"gemini_diagnostics"
    out.mkdir(parents=True, exist_ok=True)
    key=os.environ.get("GEMINI_API_KEY")
    if not key:
        write(out/"gemini_skipped.json", {"generatedAt":now(),"status":"skipped","reason":"GEMINI_API_KEY yok"})
        print("Gemini skipped")
        return
    files=sorted(Path(args.raw_root).glob("**/*.html"))[:args.max_files]
    results=[]
    for f in files:
        raw=f.read_text(encoding="utf-8", errors="replace")[:60000]
        prompt=json.dumps({
            "task":"TFF HTML parser diagnostic. Veri üretme; sadece parser problemi ve öneri yaz.",
            "file":str(f),
            "schema":{
                "containsBalikesirspor":"boolean",
                "looksLikeMatchDetail":"boolean",
                "looksLikeStandings":"boolean",
                "encodingProblem":"string",
                "parserProblem":"string",
                "suggestedRule":"string",
                "confidence":"high|medium|low"
            },
            "text":strip_html(raw)
        }, ensure_ascii=False)
        try:
            resp=call(key,args.model,prompt)
            txt=response_text(resp)
            try: parsed=json.loads(txt)
            except Exception: parsed={"rawResponse":txt}
            parsed["file"]=str(f)
            results.append(parsed)
        except Exception as ex:
            results.append({"file":str(f),"error":str(ex)})
        time.sleep(args.sleep)
    write(out/"gemini_summary.json", {"generatedAt":now(),"status":"ok","model":args.model,"filesAnalyzed":len(files),"results":results})
    print("Gemini diagnostics written")
if __name__=="__main__":
    main()

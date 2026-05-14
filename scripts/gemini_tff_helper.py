#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini TFF Helper

This script never writes app data.
It only creates diagnostic JSON files under reports/tff_factory/gemini_diagnostics.

Use:
  GEMINI_API_KEY=... python scripts/gemini_tff_helper.py --reports-root reports/tff_factory --raw-root sources/tff/raw

Gemini is not a data source. It is only a parser/diagnostic assistant.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def read_text(path: Path, limit: int = 12000) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def strip_html(raw: str) -> str:
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.I|re.S)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.I|re.S)
    raw = re.sub(r"<[^>]+>", "\n", raw)
    lines = [re.sub(r"\s+", " ", x).strip() for x in raw.splitlines()]
    return "\n".join(x for x in lines if x)[:9000]

def call_gemini(api_key: str, prompt: str, model: str):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as res:
        return json.loads(res.read().decode("utf-8", errors="replace"))

def extract_text_response(resp):
    try:
        return resp["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return json.dumps(resp, ensure_ascii=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports-root", default="reports/tff_factory")
    ap.add_argument("--raw-root", default="sources/tff/raw")
    ap.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))
    ap.add_argument("--max-files", type=int, default=10)
    args = ap.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    out_dir = Path(args.reports_root) / "gemini_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not api_key:
        write_json(out_dir / "gemini_skipped.json", {
            "generatedAt": now(),
            "status": "skipped",
            "reason": "GEMINI_API_KEY secret/env not set"
        })
        print("Gemini skipped: GEMINI_API_KEY yok")
        return 0

    raw_root = Path(args.raw_root)
    html_files = sorted(raw_root.glob("**/*.html"))
    # Prefer small sample of latest/first files. This is diagnostic-only to avoid cost.
    html_files = html_files[:args.max_files]

    results = []
    for path in html_files:
        raw = read_text(path, 50000)
        prompt = {
            "task": "Bu resmi TFF HTML/text içeriğini Balkes Skor parser açısından teşhis et. Veri kaynağı yalnızca TFF olmalı. Uygulama verisi üretme; sadece teşhis ver.",
            "file": str(path),
            "expected_json_schema": {
                "file": "string",
                "containsBalikesirspor": "boolean",
                "detectedMatchId": "string|null",
                "detectedHomeTeam": "string|null",
                "detectedAwayTeam": "string|null",
                "detectedScore": "string|null",
                "detectedDate": "string|null",
                "looksLikeStandings": "boolean",
                "parserProblem": "string",
                "suggestedParserRule": "string",
                "confidence": "high|medium|low"
            },
            "text": strip_html(raw)
        }
        try:
            resp = call_gemini(api_key, json.dumps(prompt, ensure_ascii=False), args.model)
            txt = extract_text_response(resp)
            try:
                parsed = json.loads(txt)
            except Exception:
                parsed = {"rawResponse": txt}
            parsed["file"] = str(path)
            results.append(parsed)
            write_json(out_dir / (path.stem[:80] + ".gemini.json"), parsed)
        except Exception as ex:
            results.append({"file": str(path), "error": str(ex)})

    write_json(out_dir / "gemini_summary.json", {
        "generatedAt": now(),
        "status": "ok",
        "model": args.model,
        "filesAnalyzed": len(html_files),
        "results": results
    })
    print(f"Gemini diagnostics written: {out_dir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

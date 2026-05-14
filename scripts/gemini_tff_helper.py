#!/usr/bin/env python3
import json, os
from pathlib import Path
from datetime import datetime, timezone
def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
out=Path("reports/tff_factory/gemini_diagnostics"); out.mkdir(parents=True,exist_ok=True)
(out/"gemini_skipped.json").write_text(json.dumps({"generatedAt":now(),"status":"skipped","reason":"Bu paket Gemini diagnostic stub içerir; gerekiyorsa eski helper geri eklenebilir."},ensure_ascii=False,indent=2),encoding="utf-8")
print("Gemini skipped")

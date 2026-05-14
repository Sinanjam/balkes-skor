#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import json
p = Path("sources/tff/registry/balkes_tff_seed_registry.json")
if not p.exists():
    raise SystemExit("HATA: registry bulunamadı: sources/tff/registry/balkes_tff_seed_registry.json")
data = json.loads(p.read_text(encoding="utf-8"))
data["policy"] = "TFF-only; no standings; perfect detail parser with goals/cards/lineups/subs/stadium/matchType"
for item in data.get("seasons", []):
    if isinstance(item, dict):
        item["tryWeeklyStandings"] = False
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Registry güncellendi: tryWeeklyStandings=false")

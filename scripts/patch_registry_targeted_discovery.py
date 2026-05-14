#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import json
TARGETS = {
    "2024-2025": {"competition": "Nesine 3. Lig", "group": "2. Grup", "pageID": "1733", "grupID": "2605", "maxWeek": 30, "confidence": "high"},
    "2023-2024": {"competition": "TFF 3. Lig", "group": "4. Grup", "pageID": "1651", "grupID": "2445", "maxWeek": 28, "confidence": "high"},
    "2022-2023": {"competition": "TFF 2. Lig", "group": "Kırmızı Grup", "pageID": "1632", "grupID": "2234", "maxWeek": 38, "confidence": "high"},
    "2021-2022": {"competition": "Spor Toto 1. Lig", "group": "", "pageID": "1580", "grupID": "", "maxWeek": 38, "confidence": "high"},
    "2020-2021": {"competition": "TFF 1. Lig", "group": "", "pageID": "1530", "grupID": "", "maxWeek": 34, "confidence": "high"},
    "2019-2020": {"competition": "TFF 1. Lig", "group": "", "pageID": "1502", "grupID": "", "maxWeek": 34, "confidence": "high"},
    "2012-2013": {"competition": "Spor Toto 2. Lig", "group": "Beyaz Grup", "pageID": "1239", "grupID": "", "maxWeek": 34, "confidence": "medium"},
}
p = Path("sources/tff/registry/balkes_tff_seed_registry.json")
if not p.exists():
    raise SystemExit("HATA: registry bulunamadı: sources/tff/registry/balkes_tff_seed_registry.json")
data=json.loads(p.read_text(encoding='utf-8'))
data['policy']='TFF-only; perfect details; no standings; season-targeted discovery v2.3'
for item in data.get('seasons',[]):
    if not isinstance(item, dict):
        continue
    item['tryWeeklyStandings']=False
    sid=item.get('season')
    if sid in TARGETS:
        t=TARGETS[sid]
        item['tffPlan']=t
        item['targetPageID']=t['pageID']
        item['targetGrupID']=t.get('grupID','')
        item['maxWeek']=t.get('maxWeek',34)
        if t.get('grupID'):
            url=f"https://www.tff.org/Default.aspx?grupID={t['grupID']}&pageID={t['pageID']}"
        else:
            url=f"https://www.tff.org/Default.aspx?pageID={t['pageID']}"
        item['targetUrls']=[url]
        item['planConfidence']=t.get('confidence','medium')
p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Registry hedef sezon planları güncellendi.')

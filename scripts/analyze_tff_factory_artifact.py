#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect TFF factory artifact ZIP quality reports for legacy contamination."""
from __future__ import annotations
import json, sys, zipfile, re
from collections import Counter

def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Kullanım: python scripts/analyze_tff_factory_artifact.py artifact.zip")
    for path in sys.argv[1:]:
        print(f"\n=== {path} ===")
        with zipfile.ZipFile(path) as z:
            names=[n for n in z.namelist() if n.startswith('reports/tff_factory/seasons/') and n.endswith('_quality.json')]
            for n in sorted(names):
                q=json.loads(z.read(n).decode('utf-8'))
                season=q.get('season') or n.rsplit('/',1)[-1].replace('_quality.json','')
                rej=q.get('rejectedReasons') or {}
                modern=sum(v for k,v in rej.items() if re.search(r'date_out_of_season:202[5-9]', k))
                print(f"{season}: published={q.get('matchesPublished')} candidates={q.get('detailCandidates')} mode={q.get('candidateMode')} skipped={q.get('skipped', False)} modernLeakRejects={modern}")
                if modern:
                    print("  UYARI: Modern sezon aday sızıntısı var; legacy sezon generic discovery kullanmamalı.")
if __name__ == '__main__':
    main()

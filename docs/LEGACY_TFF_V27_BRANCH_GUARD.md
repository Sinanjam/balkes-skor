# TFF Factory v2.7 Safe Legacy Branch Guard

Bu patch v2.6'nın doğruluk kurallarını korur, sadece eski TFF arşivinde 502/503/504/timeout veren ölü dallara gereksiz istek atmayı keser.

## Değişiklik

Workflow artık doğrudan `scripts/tff_factory.py` yerine `scripts/tff_factory_v27_branch_guard.py` wrapper'ını çalıştırır.

Wrapper:

- mevcut `tff_factory` modülünü import eder,
- parse/validasyon/yazma mantığına dokunmaz,
- yalnızca `discover_legacy_pageid_probe` fonksiyonunu branch-guard'lı sürümle değiştirir.

## Doğruluk ilkesi

Sezon bazlı süre limiti yoktur. Maç kabulü hâlâ ana factory validasyonundan geçer:

- Balıkesirspor ev/deplasman ya da Balkes alanında bulunmalı,
- maç tarihi sezon sınırları içinde olmalı,
- takım bilgileri doğru parse edilmeli.

## Hızlı atlanan şey

Aynı TFF dalı, örneğin:

- `pageID + grupID`,
- `pageID + grupID + hafta`,
- `pageID + hafta`

arka arkaya/cumulative şekilde gateway hatası verirse sadece o dal terk edilir. Sezon taraması diğer pageID/grupID dallarıyla devam eder.

## Önerilen ilk test

```text
start_season: 2018-2019
max_seasons: 5
clean_database_mode: false
auto_push_main: false
run_gemini: false
skip_standings: true
legacy_broad_probe_limit: 350
strict_legacy_targets: true
```

Logda şuna benzer satırlar normaldir:

```text
fetch hızlı atla: ... -> HTTP Error 504: Gateway Time-out
```

Ama artık birkaç 504 sonrası aynı ölü hafta/grup dalı bırakılır ve tarama diğer dallara devam eder.

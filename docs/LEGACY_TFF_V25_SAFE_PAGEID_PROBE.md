# Balkes Skor TFF Factory v2.5 - Safe Legacy PageID Probe

## Sorun

Son iki artifact şunu gösterdi:

- `2018-2019` sadece `known_match_ids_only` modunda 2 maç üretiyor.
- `2017-2018`, `2016-2017`, `2015-2016`, `2014-2015` sezonları `legacy_professional_missing_exact_tff_target_no_blind_scan` nedeniyle tamamen atlanıyor.
- v2.4 bunu bilerek yapıyordu: önceki kör tarama modern/current TFF sayfalarına düşüp 2025-2026 maç ID havuzunu 2018-2019 sanıyordu. Bu doğru değil.

## Çözüm

v2.5 kör current-page taramayı geri açmaz. Onun yerine registry içine sezon bazlı dar `legacyPageIdProbe` pencereleri ekler.

Algoritma:

1. Exact `targetPageID` varsa yine onu kullanır.
2. Exact target yoksa ve `legacyPageIdProbe` varsa yalnızca tanımlı historical `pageID` aralığını tarar.
3. Grup/hafta sayfalarına sadece sayfa veya grup içinde Balıkesirspor/kulüp ID ipucu varsa genişler.
4. Sayfada macId bulunsa bile Balıkesirspor satırı seçilemiyorsa `all_ids` fallback yapılmaz.
5. Her maç detayı ayrıca `Balıkesirspor var mı?` ve `tarih sezon aralığında mı?` kontrollerinden geçmeden data'ya yazılmaz.

Bu nedenle yanlış modern sezon havuzuna düşmez, ama 2018-2019 öncesi profesyonel sezonları artık tamamen skip etmez.

## Amatör sezonlar

`2001-2002` - `2005-2006` amatör dönem olarak kalır ve TFF detail taraması yapılmaz.

## Önerilen Actions denemesi

Önce küçük doğrulama:

```text
start_season: 2017-2018
max_seasons: 4
clean_database_mode: false
auto_push_main: false
run_gemini: false
skip_standings: true
legacy_broad_probe_limit: 0
strict_legacy_targets: true
```

Raporlarda beklenen:

- `candidateMode`: `legacy_pageid_probe_selected_or_known` ya da `legacy_pageid_probe_no_selected_ids`
- `legacyPageIdProbe`: `true`
- `legacyProbeDiagnostics`: hangi pageID/grup sayfalarının Balıkesirspor ipucu verdiğini gösterir.

İlk run doğrulanınca `auto_push_main: true` ile tekrar çalıştırılabilir.

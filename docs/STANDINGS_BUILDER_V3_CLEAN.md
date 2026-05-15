# Standings Builder v3 — Clean computed-safe tables

Bu sürüm puan tablosu tarafındaki iki ana problemi düzeltir:

1. TFF resmi tablolarında yanlış parse edilen `1. Devre`, `2. Devre` gibi satırları temizler.
2. `targetPageID / targetUrls` olmayan sezonlarda, daha önce çekilmiş `data/seasons/<season>/matches_index.json` ve maç JSON'larından tablo hesaplamaya çalışır.

## Doğruluk kontrolleri

Bir puan tablosu satırı ancak şu kontrollerden geçerse kabul edilir:

- Takım adı gerçek metin olmalı; `Devre`, `Takım`, başlık/ara satır olmamalı.
- `O = G + B + M` olmalı.
- `Av = A - Y` olmalı.
- Puan değeri makul aralıkta olmalı.
- Resmi tablo kaynağı kullanılacaksa tabloda Balıkesirspor bulunmalı.

## Uygulama UI düzeltmesi

Eski uygulama tabloyu tek satır formatlı metinle gösteriyordu; telefon ekranında sütunlar kırılıyordu. `patch_android_standings_ui_v29.py` MainActivity içindeki puan durumu ekranını takım kartlarıyla gösterilecek şekilde düzenler ve uygulama tarafında da bozuk satırları filtreler.

## Önerilen komutlar

Hızlı ve temiz test:

```fish
fish run_standings_builder.fish 2024-2025 1 auto 5000 false false 6 missing smart
```

Tam doğruluk/hesaplama testi:

```fish
fish run_standings_builder.fish 2024-2025 1 computed-only 5000 false false 6 all smart
```

Tüm sezon kuyruğu:

```fish
fish run_standings_builder.fish 2025-2026 36 auto 5000 true false 6 missing smart
```

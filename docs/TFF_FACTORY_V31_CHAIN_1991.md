# TFF Factory v3.1 — 4'lü zincirli 1991 otomasyonu

Bu patch iki şeyi ekler:

1. `.github/workflows/tff_factory_chain_1991.yml`
   - 4 sezonluk grup çalıştırır.
   - Grup başarılı olursa 10 dakika bekleyip sıradaki 4'lü grubu başlatır.
   - Grup `failed` veya `timeout` olursa da rapora yazar, yine 10 dakika bekleyip sonraki gruba geçer.
   - 1990-1991 dahil olana kadar devam eder.

2. `scripts/tff_standings_builder_v31.py`
   - Puan tablosu oluştururken `data/seasons/<season>/matches_index.json` içindeki Balıkesirspor-odaklı maçlardan sahte tam lig tablosu üretmez.
   - TFF standings isteklerinde daha kısa URL timeout kullanır.
   - Puan cezası mantığı base builder'daki `data/standings_penalties.json` üzerinden korunur.

## İlk çalıştırma

İlk 4'lü grup zaten bittiyse zinciri buradan başlat:

```text
start_season: 2021-2022
end_year: 1990
group_size: 4
wait_minutes: 10
group_timeout_minutes: 300
auto_push_main: true
skip_standings: false
standings_mode: auto
standings_detail_mode: missing
standings_workers: 6
standings_week_param_mode: smart
legacy_broad_probe_limit: 350
strict_legacy_targets: true
chain_label: chain-1991
```

## Daha yüksek doğruluk

`standings_detail_mode: all` seçilebilir. Daha yavaştır ama detay doğrulaması daha güçlüdür.

## Raporlar

Her grup için şuraya durum yazılır:

```text
reports/tff_chain/<chain_label>_<group>.json
```

Durum değerleri:

- `success`
- `failed`
- `timeout`

Hepsinde zincir devam eder; sadece checkout/izin/GitHub token gibi altyapı hataları zinciri durdurabilir.

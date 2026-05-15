# TFF Factory v2.9 — Speed, Completeness, Accuracy

Bu sürüm v2.8'in doğruluk modelini korur: data'ya yazılacak her maç yine `Balıkesirspor + sezon tarihi + takım/skor/tarih` doğrulamasından geçer.

## Amaçlar

- **Hız:** Eski TFF arşivindeki ölü `pageID / grupID / hafta` URL'lerinde uzun bekleme azaltıldı.
- **Eksiksizlik:** Sezonu komple kesen süre/probe limiti yok. Ölü dal bırakılır, diğer sayfa aralıkları taranmaya devam eder.
- **Doğruluk:** Kör modern/current havuz taraması açılmadı. Yanlış sezon maçları filtrelenir.

## Yeni davranış

- Legacy probe sayfalarında per-URL timeout düşürüldü.
- Aynı branch içinde çok fazla 502/503/504/timeout veya boş hafta olursa sadece o branch terk edilir.
- Raporlarda `page_week_branch_abandoned`, `group_week_branch_abandoned`, `page_week_empty_abandoned` gibi tanılar görülebilir.

## Önerilen test

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

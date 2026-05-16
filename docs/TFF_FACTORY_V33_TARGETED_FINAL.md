# TFF Factory v3.3 — Targeted Final Rebuild

Bu sürüm zincir çalışması sonrası görülen iki ana soruna odaklanır:

1. Eski TFF sayfalarının Balıkesirspor profesyonel takım maçlarıyla birlikte U21/PAF/Akademi/BAL/Kadın gibi yan takım kayıtlarını döndürmesi.
2. Bazı sezonlarda yanlış veri yayınlamak yerine hedef sezonu `needs target / suppressed` olarak raporlamak gerekmesi.

## Hedef

- Sadece Balıkesirspor **senior/profesyonel takım** maçları yayınlanır.
- 150-250 maçlık kirli sezonlar data'ya basılmaz; filtrelenir veya bastırılır.
- Çok az maç kalan sezonlar kullanıcıya sahte sezon gibi gösterilmez.
- Puan tablosu, sadece temiz maç verisi üzerinden veya resmi TFF tablosu güvenliyse üretilir.
- Zincirde bir grup fail/timeout olsa bile sonraki gruba geçme davranışı korunur.

## Yeni workflow seçeneği

`clean_all_before_start`:

- `true`: Mevcut `data/` önce artifact backup'a alınır, sonra tamamen temizlenir.
- Zincir sonraki 4'lü grupları tetiklerken bu değer otomatik `false` geçilir.

## Önerilen temiz final run

```text
start_season: 2025-2026
end_year: 1990
group_size: 4
wait_minutes: 5
group_timeout_minutes: 300
clean_all_before_start: true
auto_push_main: true
skip_standings: false
standings_mode: auto
standings_detail_mode: missing
standings_workers: 6
standings_week_param_mode: smart
legacy_broad_probe_limit: 350
strict_legacy_targets: true
chain_label: chain-1991-v33
```

## Lokal mevcut data temizliği

```fish
python3 scripts/clean_bad_professional_data_v33.py --data-root data --reports-root reports/tff_factory --write
python3 scripts/validate_target_data_v33.py --data-root data --reports-root reports/tff_factory --strict
```

## Raporlar

- `reports/tff_factory/professional_guard_v33_summary.json`
- `reports/tff_factory/target_validation_v33.json`
- `reports/tff_chain/*.json`


## v3.3.1 live-data safety gate

The chain workflow refuses to push `main/data` when a group fails or times out and the generated manifest is empty. It also refuses any empty live manifest even if the process exits cleanly. This prevents a failed clean rebuild from replacing the app's live data with `availableSeasons: []`.

Manual clean runs use the same empty-manifest guard before commit/push.

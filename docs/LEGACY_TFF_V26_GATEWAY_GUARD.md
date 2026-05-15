# Balkes Skor TFF Factory v2.6 — Safe Legacy Gateway Guard

Bu patch v2.5 safe legacy pageID probe mantığını korur; sadece TFF eski arşiv sayfalarında görülen `502/503/504 Gateway` takılmalarını hızlı ve güvenli şekilde yönetir.

## Neyi düzeltir?

- `2018-2019` gibi sezonlarda bulunan doğru adayları kabul etmeye devam eder.
- `2017-2018` gibi eski sezonlarda bazı `pageID/grupID` dalları `504 Gateway Time-out` verirse aynı bozuk dalı dakikalarca 3 kez denemez.
- Aynı pageID/grupID/hafta dalında art arda gateway/timeout görülürse sadece o dal terk edilir.
- Sezonun tamamı süreyle kesilmez; kullanıcı özellikle doğruluk istediği için sezon bazlı zaman limiti eklenmedi.
- Kabul edilen her maç yine `Balıkesirspor var mı?` ve `tarih sezon içinde mi?` doğrulamasından geçer.
- Kör modern/current-page tarama geri açılmadı.

## Önemli davranış

Gateway guard veri uydurmaz. Ulaşılamayan dalları rapora `legacyProbeDiagnostics` içinde yazar. TFF daha sonra toparlanırsa workflow tekrar çalıştırıldığında cache/force ayarına göre yeniden denenebilir.

## Önerilen Actions ayarı

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

İlk run raporları iyi görünürse `auto_push_main: true` ile tekrar çalıştır.

## Beklenen log farkı

Eski davranış:

```text
fetch hata 1/3 ... HTTP Error 504
fetch hata 2/3 ... HTTP Error 504
fetch hata 3/3 ... HTTP Error 504
```

Yeni davranış:

```text
fetch hızlı atla: ... -> HTTP Error 504: Gateway Time-out
```

Birkaç ardışık gateway hatasından sonra kalan grup/hafta dalı atlanır, fakat diğer pageID aralığı taranmaya devam eder.

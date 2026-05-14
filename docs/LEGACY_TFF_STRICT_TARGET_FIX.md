# Legacy TFF strict-target fix

Bu paket, 2018-2019 ve daha eski sezonlarda görülen yanlış aday havuzu sorununu kapatır.

## Sorun

Eski sezonlarda `targetPageID / targetUrls` yoksa factory genel `pageIds` fallback'ine düşüyordu. Bu fallback güncel TFF sayfalarından modern `macId` değerleri yakalayabiliyor; örneğin 2018-2019 çalıştırılırken 2025-2026 tarihli maçlar aday olarak denenmişti.

## Yeni davranış

- 2018-2019 ve daha eski sezonlar `legacySeason` sayılır.
- `strict_legacy_targets=true` varsayılandır.
- Legacy sezonda exact `targetPageID`, `targetUrls` veya elle doğrulanmış `knownMatchIds` yoksa TFF'ye kör istek atılmaz; sezon raporda `legacy_professional_missing_exact_tff_target_no_blind_scan` olarak atlanır.
- Amatör sezonlar yine TFF taraması yapmadan atlanır.
- Şimdilik elle doğrulanmış tarihsel macId'ler korunur:
  - 2018-2019: `195050`, `205830`
  - 1996-1997: `41478`

## Actions input

Yeni input:

```text
strict_legacy_targets: true
```

Bunu `false` yapmak mümkündür ama önerilmez. Doğruluk için `true` bırak.

## Doğru kullanım

```text
start_season: 2018-2019
max_seasons: 5
legacy_broad_probe_limit: 350
strict_legacy_targets: true
```

Bu artık yanlış 2025 adaylarına düşmez. Exact hedefi olmayan legacy sezonları atlar; knownMatchIds olan sezonlarda sadece bu güvenli adayları dener.

## Eski sezonları tam doldurmak için

Her sezonun gerçek TFF hedefi bulunduğunda registry'ye şunlar eklenmeli:

```json
{
  "targetPageID": "...",
  "targetGrupID": "...",
  "maxWeek": 34,
  "targetUrls": ["https://www.tff.org/Default.aspx?pageID=..."]
}
```

Exact hedef eklenince aynı factory sezonu kör tarama yapmadan hedefli çalıştırır.

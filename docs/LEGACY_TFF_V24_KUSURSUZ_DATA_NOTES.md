# Balkes Skor TFF Factory v2.4 — Strict Legacy Known-Only Data Patch

Bu paket veri doğruluğunu hızdan öne alır.

## Artifact analizinden çıkan sorun

Son 2018-2019 / 2017-2018 denemelerinde eski sezonlar için generic `pageIds` fallback'i modern TFF havuzuna düşmüştü. Kalite raporlarında 2018-2019 için adayların büyük bölümünün 2025-2026 tarihli maçlar olduğu görüldü (`date_out_of_season:2025-*`). Bu yüzden eski sezonlarda blind/generic tarama doğru veri üretmez.

## Bu patch ne yapar?

- 2018-2019 ve daha eski legacy sezonlarda exact `targetPageID`, `targetUrls` veya elle doğrulanmış `knownMatchIds` yoksa TFF'ye kör tarama yapmaz.
- Elle doğrulanmış `knownMatchIds` varsa generic sayfa keşfine hiç girmez; sadece bu maç ID'lerini indirir ve sezon/takım/tarih doğrulamasından geçirir.
- `allowLegacyBroadFallback` legacy sezonlarda kapalıdır; exact hedef yoksa 350/5000 aday deneme yapılmaz.
- 2001-2002 ile 2005-2006 arası amatör dönem olarak işaretlenmiştir; TFF detay taraması yapılmaz.
- Run raporlarında `knownOnly` ve `plannedTarget` alanları eklenir.

## Şu an güvenli çekilebilen legacy parçalar

- `2018-2019`: `195050`, `205830` hand-verified known-only.
- `1996-1997`: `41478` hand-verified known-only.
- Exact target planı bulunan sezonlar mevcutsa hedefli çalışır; olmayan sezonlar skip edilir.

## Actions önerisi

İlk güvenli test:

```text
start_season: 2018-2019
max_seasons: 5
strict_legacy_targets: true
legacy_broad_probe_limit: 350
clean_database_mode: false
auto_push_main: true
```

Beklenen davranış:

- 2018-2019 sadece known ID'leri dener.
- 2017-2018, 2016-2017, 2015-2016, 2014-2015 exact hedef yoksa skip edilir.
- Modern/yanlış 2025 adaylarına düşmez.

## Yeni exact hedef ekleme kuralı

Bir sezon için exact TFF hedefi bulunursa registry'de şu alanları ekle:

```json
{
  "season": "2017-2018",
  "targetPageID": "...",
  "targetGrupID": "",
  "maxWeek": 34,
  "targetUrls": ["https://www.tff.org/Default.aspx?pageID=..."],
  "planConfidence": "high",
  "skipTff": false,
  "knownOnly": false
}
```

Exact hedef yoksa sezonu skip bırak. Bu, bozuk veri üretmekten daha güvenlidir.

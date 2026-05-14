# TFF Factory v2.2 Perfect Details No Standings

Bu sürüm maç detaylarını zenginleştirmek için hazırlandı. Puan tablosu çekmez; puan tablosu ayrı Nix standings hattındadır.

## Çekilen alanlar

- Maç kodu
- Tarih / saat
- Organizasyon
- Stat
- Ev/deplasman takımı
- Skor
- Maç türü: `league`, `cup`, `playoff`, `friendly_or_unknown`
- Hakemler / gözlemci / temsilci metinleri
- İlk 11
- Yedekler
- Teknik sorumlu
- Goller / golcüler / dakika / gol tipi
- Kartlar / kart rengi / dakika
- Oyuncu değişiklikleri
- Maçtaki tüm oyuncular için `players` listesi
- `sections_raw` ham metin yedeği

## Güvenlik

- `standings_by_week.json` boş üretilir.
- Hiç maç üretmezse workflow fail eder, main’e boş veri basmaz.
- Raw HTML repo’ya girmez; artifact olarak saklanır.

# Balkes Skor Standings Builder v2 Fast Safe

Bu patch puan tablosu hattını hız ve doğruluk için güçlendirir.

## Ana farklar

- Haftalık TFF sayfalarında artık her hafta için 5 farklı parametre denenmez. Önce `hafta` denenir; sadece sonuç yoksa fallback parametreleri denenir.
- Fikstür satırından tarih, ev/deplasman ve skor güvenli şekilde okunabiliyorsa maç detay sayfası açılmaz.
- Eksik kalan maç detayları paralel çekilir. Varsayılan `workers=4`.
- Her takım hafta 1'den itibaren tabloya dahil edilir; bay geçen ya da geç fikstüre giren takım sonradan tabloya “zıplamaz”.
- Commit/push modunda raw HTML ve tee log dosyaları commitlenmez; yalnızca data ve JSON raporları alınır.
- Eski/amatör dönem skip mantığı korunur. Exact TFF hedefi olmayan sezonda hâlâ kör tarama yapılmaz.

## Önerilen güvenli komut

```fish
cd ~/balkes-skor
nix develop
fish run_standings_builder.fish 2024-2025 1 auto 2500 false false 4 missing smart
```

Parametreler:

```text
1  start season         2024-2025
2  kaç sezon            1
3  mode                 auto / official-only / computed-only
4  probe limit          2500
5  auto push            true / false
6  force refetch        true / false
7  workers              4 önerilir; çok nazik mod için 1
8  detail mode          missing / all / none
9  week param mode      smart / fast / wide
```

## Doğruluk modu

Liste satırları yetmezse veya her detayı TFF maç detayından doğrulamak istersen:

```fish
fish run_standings_builder.fish 2024-2025 1 computed-only 5000 false false 4 all smart
```

## Hızlı mod

TFF haftalık fikstür satırları temiz çıkıyorsa:

```fish
fish run_standings_builder.fish 2024-2025 1 computed-only 5000 false false 4 none fast
```

Bu mod maç detaylarını hiç açmaz; sadece haftalık sayfa satırlarından tablo üretir. Kontrol amaçlı kullanılmalı.

## Gece bırakılacak öneri

```fish
git pull --rebase origin main
fish run_standings_builder.fish 2025-2026 36 auto 5000 true false 4 missing smart
```

`true` olan 5. parametre iş bitince commit + push yapar.

## Raporlar

Her sezon için:

```text
reports/standings/<season>.json
```

Son özet:

```text
reports/standings/last_run_summary.json
```

Yeni raporlarda `fetchStats` alanı bulunur:

```json
{
  "weeklyPagesFetched": 30,
  "listingRowsParsed": 240,
  "detailCandidates": 240,
  "listingDetailsUsed": 210,
  "detailFetchNeeded": 30
}
```

Bu alan sayesinde darboğazın haftalık sayfa mı, listing parser mı, detay fetch mi olduğu hızlı görülür.

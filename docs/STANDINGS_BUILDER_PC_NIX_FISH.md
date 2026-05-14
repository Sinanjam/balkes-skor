# Balkes Skor Puan Tablosu Hattı — PC / NixOS / Fish

Bu paket, puan tablosu işini GitHub Actions'tan ayırır. Araç yerel bilgisayarda çalışır, sezonların haftalık puan tablolarını üretir ve istenirse bittiğinde commit + push yapar.

## Mantık

1. Önce TFF sezon/hafta sayfalarında resmi haftalık puan tablosu arar.
2. Resmi haftalık tablo bulunamazsa aynı sezonun lig maç detaylarını toplar.
3. Lig maçlarından hafta hafta tablo hesaplar.
4. `data/standings_penalties.json` içindeki puan cezalarını/ek puan kararlarını hesaplanan tablolara uygular.
5. Çıktıyı uygulamanın zaten okuduğu dosyaya yazar:

```text
data/seasons/<sezon>/standings_by_week.json
```

Uygulama Balıkesirspor satırını `isBalkes: true` alanından vurgular. Bu pakette Android ekranında satıra averaj/atılan/yenen ve ceza notu gösterimi de eklendi.

## Kurulum

```fish
nix develop
```

## İlk çalıştırma

Tek sezon, otomatik mod:

```fish
fish run_standings_builder.fish 2024-2025 1 auto 2500 false
```

Beş sezon, otomatik mod, bitince commit + push:

```fish
fish run_standings_builder.fish 2024-2025 5 auto 2500 true
```

Parametreler:

```text
1: start_season      Örnek: 2024-2025
2: max_seasons       Örnek: 5
3: mode              auto | official-only | computed-only
4: probe_limit       Maç detay fallback tarama limiti
5: auto_push         true | false
6: force             true | false, cache'i yok sayıp yeniden çeker
```

## Önerilen gece akışı

Önce güncel/planı net sezonlar:

```fish
fish run_standings_builder.fish 2024-2025 6 auto 2500 true
```

Sonra eski profesyonel paketler, registry planları hazır oldukça:

```fish
fish run_standings_builder.fish 2018-2019 5 auto 2500 true
fish run_standings_builder.fish 2013-2014 5 auto 2500 true
fish run_standings_builder.fish 2008-2009 3 auto 2500 true
```

Amatör olarak işaretlenen sezonlarda araç TFF profesyonel taramasını atlar; boşa TFF isteği yapmaz.

## Puan cezaları

Cezalar şu dosyada tutulur:

```text
data/standings_penalties.json
```

Örnek gerçek kayıt formatı:

```json
{
  "team": "BALIKESİRSPOR",
  "points": -3,
  "effectiveWeek": 1,
  "note": "TFF kararı ...",
  "sourceUrl": "https://...",
  "sourceNote": "Karar/duyuru tarihi ..."
}
```

`points` negatifse ceza, pozitifse iade/ek puandır. `effectiveWeek` kararın hangi haftadan itibaren tabloda görüneceğini belirler.

> Not: Resmi TFF tablosu yakalanırsa cezanın zaten resmi tabloda işlendiği varsayılır. Maçlardan hesaplanan fallback tabloda bu dosyadaki ceza uygulanır.

## Raporlar

Her sezon için rapor:

```text
reports/standings/<sezon>.json
```

Son çalışma özeti:

```text
reports/standings/last_run_summary.json
```

Raporlarda şu alanlara bak:

- `source`: `official_tff_weekly_table` veya `computed_from_tff_results`
- `weeksGenerated`
- `matchesUsed`
- `teams`
- `penaltiesApplied`
- `warnings`
- `balkesFinal`

## Veri güvenliği

Araç, yeterli lig maçı bulamazsa varsayılan olarak partial tablo yazmaz. Bu yanlış/eksik tabloyu uygulamaya basmamak için güvenlik freni olarak bırakıldı.

Partial tablo zorunlu gerekiyorsa doğrudan Python scriptinde şu bayrak kullanılabilir:

```fish
python3 scripts/tff_standings_builder.py --start-season 2024-2025 --max-seasons 1 --allow-partial
```

# Balkes Skor 2025-2026 Veri Dönüştürme Raporu

## Kaynak
- Kaynak zip: `balkes-tff-2025-2026.zip`
- Kaynak türü: TFF açık HTML sayfaları
- Sezon: 2025-2026
- Lig/grup: Nesine 3. Lig / 04. Grup
- Dönüştürme zamanı: 2026-05-11T03:54:45Z

## Üretilen uygulama veri yapısı
- `data/manifest.json`
- `data/search_index.json`
- `data/seasons/2025-2026/season.json`
- `data/seasons/2025-2026/matches_index.json`
- `data/seasons/2025-2026/standings_by_week.json`
- `data/seasons/2025-2026/matches/*.json`
- `data/assets/logo_balkes_skor.png`
- `assets/logo_balkes_skor_source.png`
- `assets/android_res/mipmap-*/ic_launcher.png`

## Sayısal özet
- Uygulamaya alınan Balıkesirspor maçı: **32**
- Lig maçı: **30**
- Play-off maçı: **2**
- Haftalık puan durumu snapshot: **30**
- Detay sayfasından ilk 11’i iki takım için de çıkan maç: **32/32**
- Olay kaydı toplamı: **540**
- Gol olayı: **89**
- Kart olayı: **172**
- Oyuncu değişikliği olayı: **279**

## Balıkesirspor lig özeti
- Oynanan: **30**
- Galibiyet/Beraberlik/Mağlubiyet: **17/7/6**
- Gol: **59-24**
- Averaj: **35**
- Son puan durumu satırı: **5. sıra, 58 puan**

## Notlar
- Logo/resim veri taramasından çekilmedi; uygulama logosu olarak bu konuşmada üretilen **Balkes Skor** logosu eklendi.
- TFF HTML içindeki kulüp logo bağlantıları uygulama verisine indirilmiş görsel olarak alınmadı.
- `raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/` tabanına göre manifest hazırlandı.
- GitHub Actions dosyası eklenmedi.
- Uygulama içinde maç listesi için `matches_index.json`, maç detayı için `matches/{macId}.json`, puan durumu için `standings_by_week.json` okunmalı.

## Repoya basma

Fish için paket içinden:

```fish
./PUSH_DATA.fish ~/Downloads/balkes-skor
```

Bu komut build yapmaz; sadece `data/`, `app_logo_assets/` ve rapor dosyalarını repoya kopyalayıp commit/push yapar.

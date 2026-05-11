# Balkes Skor Paket Raporu

Bu paket, önceki 2025-2026 TFF tarama çıktısından üretilen temiz uygulama verisini ve Android beta/debug iskeletini içerir.

## Uygulama

- Paket adı: `com.sinanjam.balkesskor`
- Debug applicationId: `com.sinanjam.balkesskor.debug`
- Uygulama adı: `Balkes Skor`
- Version: `0.1.0-beta-debug`
- Minimum SDK: 23
- Compile SDK: 35
- UI: Native Java Activity, XML layout yok
- Actions: yok

## Veri

- Sezon: 2025-2026
- Lig: Nesine 3. Lig, 04. Grup
- Maç: 32
- Lig maçı: 30
- Play-off maçı: 2
- Haftalık puan durumu: 30
- İlk 11/yedek verisi: maç detay JSON'larında var
- Olaylar: gol, kart ve oyuncu değişiklikleri

## Logo

TFF'den logo/resim indirilmedi. Uygulama logosu olarak üretilen `Balkes Skor` logosu kullanıldı.

## İnternet veri akışı

Uygulama önce GitHub raw linklerinden veri çeker:

```text
https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/
```

Bağlantı yoksa önce cache, cache yoksa APK içindeki `assets/data/` fallback verisini kullanır.

## Build + publish + release

Ana komut:

```fish
./BUILD_PUSH_RELEASE.fish
```

Bu komut build alır, kodları repoya pushlar ve APK'yı GitHub prerelease olarak yükler.

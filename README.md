# Balkes Skor

Balıkesirspor odaklı maç merkezi uygulaması. Bu ilk beta/debug sürüm, 2025-2026 sezonu için TFF açık verilerinden dönüştürülen JSON dosyalarını GitHub raw üzerinden okuyacak şekilde hazırlandı.

## Özellikler

- Ana sayfa: sezon özeti, son kayıtlı maç, hızlı erişim
- Maçlar: 30 lig + 2 play-off maçı
- Maç detayı: skor, tarih, stat, hakemler, olaylar, ilk 11 ve yedekler
- Puan durumu: 30 haftalık puan durumu snapshot'ı
- GitHub raw veri okuma + cache + asset fallback
- Balkes Skor logosu ve launcher iconları
- GitHub Actions yoktur

## Veri kaynağı

Uygulama varsayılan olarak şuradan okur:

```text
https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/
```

Veri klasörü:

```text
data/
  manifest.json
  search_index.json
  assets/logo_balkes_skor.png
  seasons/2025-2026/
    season.json
    matches_index.json
    standings_by_week.json
    matches/*.json
```

## Build + push + beta/debug release

Fish:

```fish
cd ~/Downloads/balkes-skor
./BUILD_PUSH_RELEASE.fish
```

Bu komut:

1. Nix geçici Android/Gradle ortamı açar.
2. Debug APK üretir.
3. Güncel kodları ve `data/` klasörünü git commit/push yapar.
4. Oluşan `BalkesSkor-beta-debug.apk` dosyasını GitHub'da prerelease olarak yayımlar.

GitHub release için `gh auth login` daha önce yapılmış olmalı.

## Sadece lokal APK

```fish
cd ~/Downloads/balkes-skor
./BUILD_LOCAL_DEBUG.fish
```

APK çıkışı:

```text
~/Downloads/balkes-skor/BalkesSkor-beta-debug.apk
```


## Nix Android SDK notu

Bu paket Nix ortamında hem Android Build-Tools 34.0.0 hem de 35.0.0 içerir. Gradle bazı ortamlarda 34.0.0 isteyebildiği için /nix/store yazma hatasını önlemek üzere ikisi birlikte compose edilmiştir.

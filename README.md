# Balkes Skor

Balıkesirspor odaklı maç merkezi uygulaması.

## v0.5.0-beta-debug

- Paket adı: `com.sinanjam.balkesskor`
- Tema: sadece karanlık tema
- Veri kaynağı: `https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/`
- Uygulama internet olmadan çalışmaz; bağlantı yoksa splash sonrası uyarı verir.
- Splash ekranında GitHub latest release kontrolü yapılır.
- Güncelleme varsa kullanıcı GitHub latest release sayfasına yönlendirilir.
- GitHub Actions yoktur; APK yerelde build edilir ve Nix ortamındaki `gh` ile release edilir.

## Build + push + latest release

Fish:

```fish
cd ~/Downloads/balkes-skor
./BUILD_PUSH_RELEASE.fish
```

Bu komut Nix Android ortamını açar, debug APK üretir, kodu/veriyi GitHub'a pushlar ve APK'yı latest release olarak yayınlar.

APK linki:

```text
https://github.com/Sinanjam/balkes-skor/releases/latest/download/BalkesSkor-beta-debug.apk
```

## Veri güncelleme

Yeni TFF taraması aynı `data/` şemasına dönüştürüldüğünde uygulama güncellemesi gerekmez. Sadece `data/` klasörü GitHub'a gönderilir; uygulama açılışta GitHub'daki güncel manifest ve sezon dosyalarını okur.

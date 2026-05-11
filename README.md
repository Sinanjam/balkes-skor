# Balkes Skor

Balıkesirspor odaklı maç merkezi uygulaması.

## Bu sürüm

- Paket adı: `com.sinanjam.balkesskor`
- Sürüm: `0.2.1-beta-debug`
- Tema: sadece karanlık tema
- Veri kaynağı: `https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/`
- Uygulama internet olmadan çalışmaz; bağlantı yoksa splash sonrası uyarı verir.
- Splash ekranında GitHub latest release kontrolü yapılır.
- Güncelleme varsa kullanıcı GitHub latest release sayfasına yönlendirilir.
- GitHub Actions yoktur; APK yerelde build edilir ve `gh` ile release edilir.

## Build + push + latest release

Fish:

```fish
cd ~/Downloads/balkes-skor
./BUILD_PUSH_RELEASE.fish
```

Bu komut:

1. Nix Android ortamını açar.
2. Debug APK üretir.
3. Kod ve verileri GitHub'a pushlar.
4. APK'yı `BalkesSkor-beta-debug.apk` adıyla GitHub release asset'i olarak yükler.
5. Release tag'i `v0.2.1-beta-debug` olur.

APK linki:

```text
https://github.com/Sinanjam/balkes-skor/releases/latest/download/BalkesSkor-beta-debug.apk
```

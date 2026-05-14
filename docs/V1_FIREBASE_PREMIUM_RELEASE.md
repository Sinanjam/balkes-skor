# Balkes Skor v1.0.0 Firebase Premium Release

Bu patch uygulamayı v1.0.0 final görünümüne taşır ve Hakkında ekranına Firebase tabanlı son 30 gün aktif kullanıcı sayacı ekler.

## Kurulum

```fish
cd ~/balkes-skor
unzip -o ~/Downloads/balkes-skor-v1-firebase-premium-final-patch.zip -d .
sudo chown -R (id -u):(id -g) .
```

`app/google-services.json` dosyasının production paket adı `com.sinanjam.balkesskor` için olduğundan emin ol.

## Commit + release

```fish
git add -A
git commit -m "Prepare Balkes Skor v1.0.0 Firebase premium release"
git pull --rebase origin main
git push origin main
fish RELEASE_V1_LATEST.fish
```

GitHub Actions doğrudan release APK üretir ve `latest` release olarak yayınlar.

# Firebase Active Users 30D GitHub Actions Fix

Bu workflow Blaze gerektirmeden son 30 günde aktif kurulum sayısını GitHub Actions üzerinden hesaplar.

## Neden hata veriyordu?

Eski workflow `FIREBASE_SERVICE_ACCOUNT_BALKES_SKOR` secret içeriğini direkt JSON dosyasına yazıyordu. Service account JSON içindeki `private_key` alanı GitHub secret'a yanlış yapıştırılırsa JSON bozulur ve şu hata oluşur:

```text
File /tmp/firebase-service-account.json is not a valid json file.
JSONDecodeError: Invalid control character
```

## Önerilen secret

Raw JSON yerine base64 secret kullan:

```bash
base64 -w0 ~/Downloads/service-account.json
```

GitHub repo içinde:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
Name: FIREBASE_SERVICE_ACCOUNT_B64
Value: base64 çıktısı
```

Ayrıca şu secret kalmalı:

```text
FIREBASE_PROJECT_ID=balkes-skor
```

Eski `FIREBASE_SERVICE_ACCOUNT_BALKES_SKOR` secret'ı dursa da olur; yeni workflow önce `FIREBASE_SERVICE_ACCOUNT_B64` kullanır.

## Veri çekme workflow'u ile aynı anda çalışır mı?

Evet. Bu workflow repoya commit/push yapmaz; sadece Firestore'daki `public_stats/app` dokümanını günceller. TFF data workflow'u ise `data/` ve rapor dosyalarıyla çalışır. Aynı anda çalışmaları normaldir.

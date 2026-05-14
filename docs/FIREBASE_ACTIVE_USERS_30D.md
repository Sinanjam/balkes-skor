# Firebase aktif kullanıcı sayacı

Bu yapı production paket adı `com.sinanjam.balkesskor` için hazırlanmıştır. Debug applicationId suffix kullanılmaz.

## Android tarafı

Uygulama açıldığında Firebase Installation ID ile şu doküman güncellenir:

```text
app_activity/{installationId}
```

Alanlar:

```json
{
  "lastSeen": "server timestamp",
  "platform": "android",
  "appVersion": "1.0.0"
}
```

Hakkında ekranı sadece şu hazır sayıyı okur:

```text
public_stats/app.activeUsers30d
```

## Firebase deploy

Firebase CLI kuruluyken repo kökünde:

```fish
firebase login
firebase use --add
firebase deploy --only firestore:rules
firebase deploy --only functions
```

İlk sayıyı hemen hesaplatmak için deploy sonrası Firebase Console'dan `refreshActiveUsers30dManual` fonksiyon URL'sini bir kez açabilirsin. Sonrasında `refreshActiveUsers30d` saatlik çalışır.

## App Check

Yayın öncesi App Check / Play Integrity açılması önerilir. App Check açılana kadar rules yazma alanlarını dar tutar; kullanıcılar `app_activity` listesini okuyamaz.

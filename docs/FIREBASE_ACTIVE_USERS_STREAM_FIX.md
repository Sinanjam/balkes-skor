# Firebase Active Users 30D Stream Fix

Bu patch `scripts/firebase_active_users_30d.py` dosyasını aggregation/count sorgusu yerine `app_activity` koleksiyonunu stream ederek sayacak şekilde değiştirir.

Amaç:

- Firestore'da `app_activity` belgeleri görünmesine rağmen `activeUsers30d=0` dönen durumu teşhis etmek ve düzeltmek.
- Loglara `appActivityDocs`, `missingLastSeen`, `recentSample`, `cutoffUtc` alanlarını yazmak.
- `public_stats/app` içine `activeUsers30d`, `totalInstallationsTracked`, `missingLastSeen`, `cutoffUtc` yazmak.

Bu kullanım küçük ölçekli olduğu için 6 saatte bir birkaç belge okumak maliyet açısından güvenlidir. Kullanıcı sayısı büyürse aggregation count'a geri dönülebilir.

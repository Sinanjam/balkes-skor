# Balkes Skor v0.2 Raporu

## İstenen maddeler

1. TFF tarama verileri tasnif edilip uygulama formatındaki `data/` yapısına dönüştürüldü.
2. Görünüm karanlık, şık ve pratik olacak şekilde yeniden düzenlendi.
3. Tema değiştirme kaldırıldı; sadece karanlık tema var.
4. Uygulama içinde kullanıcıyı ilgilendirmeyen kaynak/cache/debug yazıları kaldırıldı.
5. İnternet yoksa uygulama çalışmaz; splash sonrası `Uygulama için internete bağlanın` ekranı gösterilir.
6. Yükleniyor temalı splash screen eklendi.
7. Ana sayfa, maçlar, maç detayı, puan durumu ve oyuncular ekranları sadeleştirildi.
8. Geri tuşu önceki ekrana döner; ana ekranda çıkış onayı sorulur.
9. Splash sırasında GitHub latest release kontrolü yapılır; güncel değilse GitHub latest release sayfasına yönlendirir.
10. `BUILD_PUSH_RELEASE.fish` yerelde build alır, kodu pushlar ve APK'yı latest release tarafına yükler.

## Veri tasnifi

- Büyük tarama: `balkes-tff-veri.zip`
- Gezilen TFF sayfası: 9000
- Bulunan maç detay sayfası: 117
- Uygulamaya alınan profesyonel maç detayı: 104
- Önceki temiz 2025-2026 verisiyle toplam uygulama maçı: 136
- Oyuncu indeksi: 190 oyuncu
- Rakip indeksi: 70 rakip

## Sezonlar

- 2025-2026: 33 maç
- 2024-2025: 32 maç
- 2023-2024: 28 maç
- 2022-2023: 37 maç
- 2009-2010: 1 maç
- 1994-1995: 1 maç
- 1992-1993: 1 maç
- 1991-1992: 1 maç
- 1990-1991: 2 maç

## Not

Büyük taramada haftalık puan durumu snapshot'ı çıkmadı. Bu yüzden puan durumu ekranında şu an güvenilir haftalık puan durumu sadece 2025-2026 sezonu için gösterilir. Diğer sezonlarda maçlar ve maç detayları gösterilir.

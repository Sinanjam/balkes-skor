# Balkes Skor v0.5 Raporu

## Yapılanlar

1. Veriler uygulama formatındaki `data/` yapısında tutuldu; yeni TFF taraması aynı şemaya eklendiğinde uygulama güncellemesi gerektirmeden GitHub üzerinden okunur.
2. Görünüm karanlık tema, kırmızı-beyaz vurgu, sade kartlar ve pratik alt/üst navigasyonla düzenlendi.
3. Tema değiştirme kaldırıldı; sadece karanlık tema var.
4. Kullanıcıyı ilgilendirmeyen debug/cache/kaynak ayrıntıları uygulama ekranlarından kaldırıldı.
5. İnternet yoksa uygulama çalışmaz; splash sonrası `Uygulama için internete bağlanın` ekranı gösterilir.
6. Yükleniyor temalı splash screen eklendi.
7. Ana sayfa, maçlar, maç detayı, puan durumu, yıllar, oyuncular ve hakkında ekranları düzenlendi.
8. Geri tuşu önceki ekrana döner; ana ekranda çıkış onayı sorulur.
9. Splash sırasında GitHub latest release kontrolü yapılır; güncel değilse GitHub latest release sayfasına yönlendirir.
10. Sol üstteki uygulama logosunda görünen siyah köşe/arka plan problemi giderildi.
11. Yıllara göre kıyas ekranı sağa kaydırdıkça eski sezonlara gidecek şekilde ayarlandı.
12. Oyuncu kartları tıklanabilir hale getirildi; maç, ilk 11, yedek, gol, kart ve sezon sayısı gösterilir.
13. Hakkında ekranı eklendi.
14. `BUILD_PUSH_RELEASE.fish` yerelde build alır, kodu pushlar ve APK'yı latest release tarafına yükler.

## Hakkında metni

- Sadece TFF sitelerinden çekebildiğimiz veriler baz alınmıştır.
- Kaynak Kodları: https://github.com/Sinanjam/balkes-skor.git
- Web sitesi: https://sinanjam.github.io/balkes-skor-web/

## Güvenlik / veri notu

Uygulamada kapalı API, kullanıcı hesabı, token veya gizli veri kullanılmaz. Veriler GitHub üzerindeki açık JSON dosyalarından okunur. Release işlemi kullanıcının yerel ortamındaki GitHub CLI oturumuyla yapılır; paket içinde token bulunmaz.

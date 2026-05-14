# TFF Factory v2.2 No Standings Fixed3

Bu sürüm, son artifact/log üzerinden görülen `score_missing` hatasını düzeltmek için hazırlanmıştır.

## Düzeltilen ana sorun

TFF maç detay sayfalarında skor çoğu zaman `2-1` metni olarak değil, iki ayrı HTML span içinde gelir:

- `lblTakim1Skor`
- `Label12` / `lblTakim2Skor`

Önceki parser sadece `2-1` gibi düz metin aradığı için bütün detayları `score_missing` diye reddediyordu.

## Bu sürüm ne yapar?

- Puan tablosu çekmez.
- Takım adlarını TFF detay sayfasındaki `lnkTakim1` / `lnkTakim2` alanlarından alır.
- Skoru TFF skor spanlerinden alır.
- Tarihi `lblTarih` alanından alır.
- Maç kodunu `lblKod` alanından alır.
- Organizasyon bilgisini `lblOrganizasyonAdi` alanından alır.
- Hakemleri hakem linklerinden toplar.
- selectedIds varsa sadece selected/known adayları dener; boşsa allDiscovered fallback yapar.
- Skorsuz ama tarihli Balıkesirspor fikstürlerini `played=false` olarak kabul eder.
- Hiç maç üretmezse workflow fail olur ve main'e basmaz.

Puan tablosu işi ayrı Nix standings projesine bırakılmıştır.


## Installer düzeltmesi

Fish içinde Bash heredoc kullanılmaz. Registry güncellemesi `scripts/disable_standings_in_registry.py` ile yapılır.

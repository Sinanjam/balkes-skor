# Legacy TFF Backfill Notes

Bu paket 1990-1991'e kadar sezon kuyruğunu güvenli çalıştırmak için hazırlanmıştır.

## Ana değişiklikler

- 2001-2002, 2002-2003, 2003-2004, 2004-2005 ve 2005-2006 sezonları amatör dönem olarak işaretlendi.
- Bu amatör sezonlarda TFF profesyonel maç detayı beklenmediği için tarama yapılmaz.
- 2018-2019'dan 1990-1991'e kadar profesyonel dönem sezonlarına lig dönemi bilgisi eklendi.
- Exact `targetPageID` bilinmeyen eski profesyonel sezonlarda önce dar `selectedIds` denenir.
- Dar adaylar sıfır maç üretirse, sadece o zaman sınırlı legacy geniş fallback devreye girer.
- Yayınlanacak maç yine de Balıkesirspor + sezon tarihi + takım doğrulamasından geçmek zorundadır.

## Fish / Nix kullanımı

```fish
nix develop
fish run_tff_factory.fish 2018-2019 5 350
```

Argümanlar:

1. başlangıç sezonu
2. kaç sezon işleneceği
3. eski profesyonel sezonlarda geniş fallback limit değeri

Örnekler:

```fish
fish run_tff_factory.fish 2018-2019 5 350
fish run_tff_factory.fish 2013-2014 4 150
fish run_tff_factory.fish 2005-2006 6 150
```

`2005-2006` başlangıçlı örnekte amatör sezonlar atlanır; sıra profesyonel sezona geldiğinde tarama devam eder.

## Not

Bu patch puan tablosu üretmez. Puan tablosu ayrı Nix standings hattında ele alınacaktır.

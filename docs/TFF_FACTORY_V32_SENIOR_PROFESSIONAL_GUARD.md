# TFF Factory v3.2 — Senior Professional Guard

Bu sürüm, zincirli taramada görülen en tehlikeli veri hatasını düzeltir: TFF eski sayfaları Balıkesirspor profesyonel takım maçlarıyla birlikte U21/PAF/akademi/BAL maçlarını da döndürebiliyor. Bu yüzden bazı sezonlarda 30-40 maç yerine 150-250 maç yayınlanmıştı.

## Yeni güvenlik kuralları

- Sadece senior/profesyonel takım müsabakaları yayınlanır.
- `U21`, `PAF`, `Akademi`, `Gelişim`, `U19/U17/U16/U15/U14`, `BAL Takımı`, `Bölgesel Amatör`, `Kadın`, `Rezerv` gibi kayıtlar reddedilir.
- Bir sezon 80 maç üstüne çıkarsa yayın bastırılır; bu genellikle yanlışlıkla birden fazla takım kategorisi çekildiğini gösterir.
- Bir sezon 8 profesyonel lig maçının altındaysa yayın bastırılır; sadece birkaç kupa maçından sezon verisi üretmez.
- Boş veya kısmi sezon klasörü yazmak yerine rapora `publicationSuppressed` / `suppressionReasons` düşer.

## Ek temizleyici

`scripts/clean_bad_professional_data_v32.py` mevcut `data/` klasörünü de temizler:

```fish
python3 scripts/clean_bad_professional_data_v32.py --data-root data --reports-root reports/tff_factory --write
```

Bu komut:

- profesyonel takım dışı maçları siler,
- kirli/kısmi sezonleri bastırır,
- `manifest.json`, `opponents_index.json`, `search_index.json`, `data_report.json` dosyalarını yeniden üretir,
- raporu `reports/tff_factory/professional_guard_v32_summary.json` içine yazar.

## Workflow değişiklikleri

- `tff_factory_chain_1991.yml` artık `scripts/tff_factory_v32_senior_professional_guard.py` çağırır.
- Factory sonrası otomatik olarak `clean_bad_professional_data_v32.py --write` çalışır.
- Standing builder, sadece temizlenmiş profesyonel takım verisi üzerinden çalışır.
- Commit öncesi raw HTML kalıntıları temizlenir; rebase dirty tree hatası azaltılır.

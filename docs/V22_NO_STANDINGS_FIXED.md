# TFF Factory v2.2 No Standings Fixed

Bu sürüm, önceki v2.2 clean-db run'ında görülen iki ana problemi hedefler:

1. Puan tablosu/weekly standings çekimi kapatıldı.
   - `parse_standings()` boş liste döndürür.
   - Registry içinde `tryWeeklyStandings=false`.
   - Puan tablosu ayrı Nix standings projesiyle üretilecek.

2. `hits=0` hatasına karşı detay parser/doğrulama tarafı güçlendirildi.
   - Tek satır takım-skor formatı yakalanır.
   - Skor ayrı satırdaysa yakındaki takım satırlarıyla eşleştirilir.
   - Türkçe ay adlarıyla tarih parse edilir.
   - `selectedIds` varsa bütün 986 ID yerine önce selected/known ID adayları doğrulanır.
   - Rejected sample ID'leri kalite raporuna yazılır.

Not:
- Bu sürüm hâlâ veri uydurmaz.
- Tarih yoksa maç kabul edilmez; ama rejectedReasons/rejectedSamples ile sebebi rapora düşer.
- Main'e boş database basma koruması devam eder.

# Veri Raporu

Veri klasörü uygulamanın GitHub raw üzerinden okuyacağı forma getirildi.

```text
data/
  manifest.json
  search_index.json
  players_index.json
  opponents_index.json
  data_report.json
  assets/logo_balkes_skor.png
  seasons/<sezon>/
    season.json
    matches_index.json
    standings_by_week.json
    matches/<macId>.json
```

Ham fixture-window kayıtları doğrudan maç olarak kullanılmadı; ekranda yalnızca detay sayfası doğrulanmış maçlar gösterilir.

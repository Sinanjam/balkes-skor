#!/usr/bin/env fish
set START_SEASON "2025-2026"
set MAX_SEASONS "1"
if test -n "$argv[1]"
    set START_SEASON "$argv[1]"
end
if test -n "$argv[2]"
    set MAX_SEASONS "$argv[2]"
end

mkdir -p reports/tff_factory sources/tff/raw
set LOG reports/tff_factory/run_(date +%Y%m%d_%H%M%S).log

echo "Balkes TFF Factory Final başlıyor"
echo "Kaynak: sadece TFF"
echo "Başlangıç sezonu: $START_SEASON"
echo "Sezon sayısı: $MAX_SEASONS"
echo "Log: $LOG"
echo

env PYTHONUNBUFFERED=1 \
python3 scripts/tff_factory.py \
  --seed sources/tff/registry/balkes_tff_seed_registry.json \
  --data-root data \
  --raw-root sources/tff/raw \
  --reports-root reports/tff_factory \
  --start-season "$START_SEASON" \
  --max-seasons "$MAX_SEASONS" \
  --sleep 1.5 2>&1 | tee "$LOG"

set STATUS $status
if test $STATUS -eq 0
    python3 scripts/validate_data.py --data-root data --min-seasons 12 --min-matches 177
    if test -n "$GEMINI_API_KEY"
        python3 scripts/gemini_tff_helper.py --reports-root reports/tff_factory --raw-root sources/tff/raw --max-files 10
    end
    echo
    echo "Bitti. Commit/push için:"
    echo "git add data sources/tff reports/tff_factory"
    echo "git commit -m 'Run TFF factory from $START_SEASON'"
    echo "git push origin main"
else
    echo "Factory hata ile durdu. Log: $LOG"
end

exit $STATUS

#!/usr/bin/env fish
set START_SEASON "2025-2026"
if test -n "$argv[1]"; set START_SEASON "$argv[1]"; end
mkdir -p reports/tff_factory sources/tff/raw
set LOG reports/tff_factory/run_v2_(date +%Y%m%d_%H%M%S).log
echo "Balkes TFF Factory v2-safe başlıyor"
echo "Sezon: $START_SEASON"
env PYTHONUNBUFFERED=1 python3 scripts/tff_factory.py --seed sources/tff/registry/balkes_tff_seed_registry.json --data-root data --raw-root sources/tff/raw --reports-root reports/tff_factory --start-season "$START_SEASON" --max-seasons 1 --sleep 1.5 2>&1 | tee "$LOG"
set STATUS $status
if test $STATUS -eq 0
    python3 scripts/validate_data.py --data-root data --min-seasons 12 --min-matches 177
    if test -n "$GEMINI_API_KEY"
        python3 scripts/gemini_tff_helper.py --reports-root reports/tff_factory --raw-root sources/tff/raw --max-files 2 --sleep 5
    end
end
exit $STATUS

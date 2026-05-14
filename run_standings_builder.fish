#!/usr/bin/env fish
set START_SEASON "2025-2026"
set MAX_SEASONS "1"
set MODE "auto"
set PROBE_LIMIT "2500"
set AUTO_PUSH "false"
set FORCE "false"

if test -n "$argv[1]"; set START_SEASON "$argv[1]"; end
if test -n "$argv[2]"; set MAX_SEASONS "$argv[2]"; end
if test -n "$argv[3]"; set MODE "$argv[3]"; end
if test -n "$argv[4]"; set PROBE_LIMIT "$argv[4]"; end
if test -n "$argv[5]"; set AUTO_PUSH "$argv[5]"; end
if test -n "$argv[6]"; set FORCE "$argv[6]"; end

mkdir -p reports/standings sources/tff/standings_raw
set LOG reports/standings/run_(date +%Y%m%d_%H%M%S).log

echo "Balkes Skor standings builder başlıyor"
echo "Sezon: $START_SEASON"
echo "Max sezon: $MAX_SEASONS"
echo "Mod: $MODE"
echo "Probe limit: $PROBE_LIMIT"
echo "Auto push: $AUTO_PUSH"
echo "Force refetch: $FORCE"

set EXTRA_ARGS
if test "$FORCE" = "true"
    set EXTRA_ARGS $EXTRA_ARGS --force
end
if test "$AUTO_PUSH" = "true"
    set EXTRA_ARGS $EXTRA_ARGS --commit --push
end

env PYTHONUNBUFFERED=1 python3 scripts/tff_standings_builder.py \
    --seed sources/tff/registry/balkes_tff_seed_registry.json \
    --data-root data \
    --raw-root sources/tff/standings_raw \
    --reports-root reports/standings \
    --penalties data/standings_penalties.json \
    --start-season "$START_SEASON" \
    --max-seasons "$MAX_SEASONS" \
    --mode "$MODE" \
    --probe-limit "$PROBE_LIMIT" \
    --sleep 1.0 \
    $EXTRA_ARGS 2>&1 | tee "$LOG"

set STATUS $pipestatus[1]
if test $STATUS -ne 0
    echo "Standings builder hata verdi. Log: $LOG"
    exit $STATUS
end

if test "$AUTO_PUSH" != "true"
    echo "Bitti. Pushlamak için:"
    echo "  git add data reports/standings app/src/main/java/com/sinanjam/balkesskor/MainActivity.java scripts/tff_standings_builder.py run_standings_builder.fish flake.nix"
    echo "  git commit -m 'Build weekly standings data'"
    echo "  git pull --rebase origin main"
    echo "  git push origin main"
end

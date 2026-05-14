#!/usr/bin/env fish
# Balkes Skor TFF factory runner for NixOS/Fish.
# Args: start_season max_seasons legacy_broad_probe_limit strict_legacy_targets force

set START_SEASON (test -n "$argv[1]"; and echo $argv[1]; or echo "2025-2026")
set MAX_SEASONS (test -n "$argv[2]"; and echo $argv[2]; or echo "3")
set LEGACY_BROAD_PROBE_LIMIT (test -n "$argv[3]"; and echo $argv[3]; or echo "350")
set STRICT_LEGACY_TARGETS (test -n "$argv[4]"; and echo $argv[4]; or echo "true")
set FORCE (test -n "$argv[5]"; and echo $argv[5]; or echo "false")

mkdir -p reports/tff_factory
set LOG reports/tff_factory/run_(date +%Y%m%d_%H%M%S).log

echo "Balkes Skor TFF factory başlıyor"
echo "Sezon: $START_SEASON"
echo "Max sezon: $MAX_SEASONS"
echo "Legacy broad probe limit: $LEGACY_BROAD_PROBE_LIMIT"
echo "Strict legacy targets: $STRICT_LEGACY_TARGETS"
echo "Force refetch: $FORCE"

set STRICT_FLAG --strict-legacy-targets
if test "$STRICT_LEGACY_TARGETS" = "false"
    set STRICT_FLAG --no-strict-legacy-targets
end

set FORCE_FLAG
if test "$FORCE" = "true"
    set FORCE_FLAG --force
end

env PYTHONUNBUFFERED=1 python3 scripts/tff_factory.py   --seed sources/tff/registry/balkes_tff_seed_registry.json   --data-root data   --raw-root sources/tff/raw   --reports-root reports/tff_factory   --start-season "$START_SEASON"   --max-seasons "$MAX_SEASONS"   --sleep 1.5   --max-discovery-probe 1500   --legacy-broad-probe-limit "$LEGACY_BROAD_PROBE_LIMIT"   $STRICT_FLAG   $FORCE_FLAG   --skip-standings 2>&1 | tee "$LOG"

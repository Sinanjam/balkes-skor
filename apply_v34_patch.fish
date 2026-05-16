#!/usr/bin/env fish
set -e
mkdir -p scripts .github/workflows docs
python3 -m py_compile \
  scripts/tff_factory_v34_targeted_professional.py \
  scripts/live_data_counts_v34.py \
  scripts/chain_plan_v34.py \
  scripts/write_next_chain_trigger_v34.py \
  scripts/write_chain_status_v34.py \
  scripts/reconcile_data_v34.py \
  scripts/validate_target_data_v34.py

if not grep -q '^__pycache__/$' .gitignore 2>/dev/null
    printf '\n__pycache__/\n' >> .gitignore
end
if not grep -q '^\*.pyc$' .gitignore 2>/dev/null
    printf '*.pyc\n' >> .gitignore
end

git rm -r --cached scripts/__pycache__ 2>/dev/null; or true

echo "v3.4 patch applied. Use: fish start_v34_chain.fish"

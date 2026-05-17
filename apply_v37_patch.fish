#!/usr/bin/env fish
set -e
mkdir -p .github/workflows .github scripts docs
printf "\n__pycache__/\n*.pyc\n" >> .gitignore
git rm -r --cached scripts/__pycache__ 2>/dev/null; or true
python3 -m py_compile \
  scripts/tff_factory_v37_targeted_professional.py \
  scripts/live_data_counts_v37.py \
  scripts/reconcile_data_v37.py \
  scripts/validate_target_data_v37.py \
  scripts/repair_plan_v37.py \
  scripts/rebuild_data_indexes_v37.py \
  scripts/tff_exact_repair_v37.py
chmod +x start_v37_repair.fish

#!/usr/bin/env fish
set -e
mkdir -p .github/workflows .github scripts docs
printf "\n__pycache__/\n*.pyc\n" >> .gitignore
git rm -r --cached scripts/__pycache__ 2>/dev/null; or true
python3 -m py_compile scripts/chain_plan_v36.py scripts/write_next_chain_dispatch_v36.py scripts/live_data_counts_v36.py scripts/write_chain_status_v36.py scripts/reconcile_data_v36.py scripts/validate_target_data_v36.py scripts/tff_factory_v36_targeted_professional.py

#!/usr/bin/env fish
set ROOT (pwd)
if not test -d .git
    echo "Bu komutu repo kökünde çalıştır: cd ~/balkes-skor"
    exit 1
end

python3 -m py_compile \
    scripts/tff_factory_v33_targeted_professional.py \
    scripts/clean_bad_professional_data_v33.py \
    scripts/validate_target_data_v33.py

echo "v3.3 targeted patch hazır."
echo "Mevcut datayı baştan başlamadan temizlemek için:"
echo "python3 scripts/clean_bad_professional_data_v33.py --data-root data --reports-root reports/tff_factory --write"
echo "python3 scripts/validate_target_data_v33.py --data-root data --reports-root reports/tff_factory --strict"

# Local Python cache files are never part of the patch.
rm -rf scripts/__pycache__ 2>/dev/null; or true

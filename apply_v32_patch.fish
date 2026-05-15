#!/usr/bin/env fish
if not test -d .git
    echo "Bu komutu repo kökünde çalıştır: cd ~/balkes-skor"
    exit 1
end
python3 -m py_compile scripts/tff_factory_v32_senior_professional_guard.py scripts/clean_bad_professional_data_v32.py
python3 scripts/clean_bad_professional_data_v32.py --data-root data --reports-root reports/tff_factory --write
printf "\nv3.2 senior professional guard uygulandı. Önerilen add:\n"
echo "git add scripts/tff_factory_v32_senior_professional_guard.py scripts/clean_bad_professional_data_v32.py .github/workflows/tff_factory_chain_1991.yml .github/workflows/tff_factory_manual_clean_db.yml docs/TFF_FACTORY_V32_SENIOR_PROFESSIONAL_GUARD.md apply_v32_patch.fish data reports/tff_factory"

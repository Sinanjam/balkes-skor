#!/usr/bin/env fish
# Apply Balkes Skor v2.9 speed/completeness/accuracy patch.
set ROOT (pwd)
if not test -d .git
    echo "Bu komutu repo kökünde çalıştır: cd ~/balkes-skor"
    exit 1
end
python3 scripts/patch_android_standings_ui_v29.py
python3 -m py_compile scripts/tff_factory_v29_speed_complete_accuracy.py scripts/tff_standings_builder.py

echo "v2.9 patch uygulandı."
echo "Önerilen add:"
echo "git add scripts/tff_factory_v29_speed_complete_accuracy.py scripts/tff_standings_builder.py scripts/patch_android_standings_ui_v29.py .github/workflows/tff_factory_manual_clean_db.yml run_standings_builder.fish app/src/main/java/com/sinanjam/balkesskor/MainActivity.java docs/STANDINGS_BUILDER_V3_CLEAN.md docs/TFF_FACTORY_V29_SPEED_COMPLETE_ACCURACY.md apply_v29_patch.fish .gitignore"

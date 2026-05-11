#!/usr/bin/env fish
set repo_dir (pwd)
if not test -f "$repo_dir/balkes-skor.nix"
    echo "HATA: balkes-skor.nix bulunamadı. Repo kökünde çalıştır."
    exit 1
end

env NIXPKGS_ALLOW_UNFREE=1 nix-shell ./balkes-skor.nix --run 'bash -lc "set -euo pipefail; echo sdk.dir=$ANDROID_HOME > local.properties; AAPT2=$ANDROID_HOME/build-tools/35.0.0/aapt2; gradle --no-daemon -Pandroid.aapt2FromMavenOverride=$AAPT2 assembleDebug; cp -f app/build/outputs/apk/debug/app-debug.apk BalkesSkor-beta-debug.apk; echo APK: $PWD/BalkesSkor-beta-debug.apk"'

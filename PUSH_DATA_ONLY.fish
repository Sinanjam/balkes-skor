#!/usr/bin/env fish
# Yeni tarama tasnifinden sonra sadece data/ klasörünü GitHub'a gönderir; APK build/release yapmaz.
set repo_dir (pwd)
set msg "Balkes Skor veri güncellemesi"
if test (count $argv) -ge 1
    set msg "$argv[1]"
end
if not test -d "$repo_dir/.git"
    echo "HATA: Git repo kökünde çalıştır."
    exit 1
end
if not test -d "$repo_dir/data"
    echo "HATA: data/ klasörü bulunamadı."
    exit 1
end

env NIXPKGS_ALLOW_UNFREE=1 nix-shell ./balkes-skor.nix --run "bash -lc 'set -euo pipefail; if gh auth status >/dev/null 2>&1; then gh auth setup-git >/dev/null 2>&1 || true; fi; git add data app/src/main/assets/data; if git diff --cached --quiet; then echo Veri değişikliği yok.; else git commit -m \"$msg\"; git push origin \$(git rev-parse --abbrev-ref HEAD); fi'"

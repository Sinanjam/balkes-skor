#!/usr/bin/env fish
set repo_dir (pwd)
if not test -f "$repo_dir/balkes-skor.nix"
    echo "HATA: balkes-skor.nix bulunamadı. Repo kökünde çalıştır."
    exit 1
end

env NIXPKGS_ALLOW_UNFREE=1 nix-shell ./balkes-skor.nix --run 'bash ./BUILD_PUSH_RELEASE.sh'

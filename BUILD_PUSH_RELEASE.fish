#!/usr/bin/env fish
set -l script_dir (cd (dirname (status --current-filename)); and pwd)
cd "$script_dir"
env NIXPKGS_ALLOW_UNFREE=1 nix-shell ./balkes-skor.nix --run 'bash ./BUILD_PUSH_RELEASE.sh'

#!/usr/bin/env bash
set -euo pipefail
TAG="v1.0.0"
TITLE="Balkes Skor v1.0.0"

if [ ! -f app/google-services.json ]; then
  echo "HATA: app/google-services.json yok. Firebase production dosyasını app klasörüne koy."
  exit 1
fi

git pull --rebase origin main

git add -A
if git diff --cached --quiet; then
  echo "Commitlenecek değişiklik yok."
else
  git commit -m "Prepare Balkes Skor v1.0.0 Firebase premium release"
fi

git push origin main

if ! command -v gh >/dev/null 2>&1; then
  echo "HATA: gh CLI yok. GitHub Actions ekranından release_latest_apk.yml workflow'unu elle çalıştırabilirsin."
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "HATA: GitHub CLI giriş yapılmamış. Önce: gh auth login"
  exit 1
fi

gh workflow run release_latest_apk.yml -f tag_name="$TAG" -f release_title="$TITLE"
echo "Workflow başlatıldı: https://github.com/Sinanjam/balkes-skor/actions"
echo "Bittiğinde latest release: https://github.com/Sinanjam/balkes-skor/releases/latest"

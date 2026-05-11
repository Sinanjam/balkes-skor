#!/usr/bin/env bash
set -euo pipefail

REPO_SLUG="${REPO_SLUG:-Sinanjam/balkes-skor}"
RELEASE_PREFIX="${RELEASE_PREFIX:-beta-debug}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-Balkes Skor beta/debug uygulama iskeleti ve veri yayını}"

if [ ! -d .git ]; then
  echo "HATA: Bu script git reposu kökünde çalışmalı."
  exit 1
fi

if [ -z "${ANDROID_HOME:-}" ]; then
  echo "HATA: ANDROID_HOME yok. Fish wrapper veya nix-shell ile çalıştır."
  exit 1
fi

cat > local.properties <<LOCAL
sdk.dir=${ANDROID_HOME}
LOCAL

AAPT2_PATH="${ANDROID_HOME}/build-tools/35.0.0/aapt2"
if [ ! -x "$AAPT2_PATH" ]; then
  AAPT2_PATH="$(find "$ANDROID_HOME" -path '*/build-tools/*/aapt2' -type f | sort | tail -n 1 || true)"
fi

GRADLE_CMD="gradle"
if [ -x "./gradlew" ]; then
  GRADLE_CMD="./gradlew"
fi

echo "== Balkes Skor beta/debug build =="
echo "Repo: $(pwd)"
echo "Android SDK: $ANDROID_HOME"
echo "AAPT2: ${AAPT2_PATH:-bulunamadı}"
echo "Gradle: $GRADLE_CMD"

if [ -n "${AAPT2_PATH:-}" ] && [ -x "$AAPT2_PATH" ]; then
  "$GRADLE_CMD" --no-daemon -Pandroid.aapt2FromMavenOverride="$AAPT2_PATH" assembleDebug
else
  "$GRADLE_CMD" --no-daemon assembleDebug
fi

APK="app/build/outputs/apk/debug/app-debug.apk"
if [ ! -f "$APK" ]; then
  echo "HATA: APK oluşmadı: $APK"
  exit 1
fi

OUT_APK="BalkesSkor-beta-debug.apk"
cp -f "$APK" "$OUT_APK"

echo "APK hazır: $(pwd)/$OUT_APK"

# local.properties ve APK .gitignore kapsamında; kaynak + data repoya basılır.
git add .
if git diff --cached --quiet; then
  echo "Commitlenecek değişiklik yok."
else
  git commit -m "$COMMIT_MESSAGE"
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "Git push: origin $BRANCH"
git push origin "$BRANCH"

if ! command -v gh >/dev/null 2>&1; then
  echo "HATA: gh CLI bulunamadı; release oluşturulamadı."
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "HATA: gh auth yapılmamış. Önce: gh auth login"
  echo "APK yine de hazır: $(pwd)/$OUT_APK"
  exit 1
fi

TAG="${RELEASE_TAG:-${RELEASE_PREFIX}-$(date -u +%Y%m%d-%H%M%S)}"
NOTES="RELEASE_NOTES.md"
if [ ! -f "$NOTES" ]; then
  cat > "$NOTES" <<NOTES_EOF
Balkes Skor beta/debug APK.

- Build tipi: debug
- Veri kaynağı: GitHub raw JSON
- GitHub Actions kullanılmadı; APK yerelde üretildi.
NOTES_EOF
fi

echo "GitHub prerelease oluşturuluyor: $TAG"
if gh release view "$TAG" --repo "$REPO_SLUG" >/dev/null 2>&1; then
  gh release upload "$TAG" "$OUT_APK" --repo "$REPO_SLUG" --clobber
else
  gh release create "$TAG" "$OUT_APK" \
    --repo "$REPO_SLUG" \
    --target "$BRANCH" \
    --title "Balkes Skor Beta Debug $TAG" \
    --notes-file "$NOTES" \
    --prerelease
fi

echo "Tamam: kod pushlandı ve debug beta APK prerelease olarak yüklendi."

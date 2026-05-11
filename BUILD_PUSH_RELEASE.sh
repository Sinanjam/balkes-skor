#!/usr/bin/env bash
set -euo pipefail

REPO_SLUG="${REPO_SLUG:-Sinanjam/balkes-skor}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-Balkes Skor v0.5 karanlık tema, yıllar, oyuncu detayı ve hakkında ekranı}"
APK_NAME="${APK_NAME:-BalkesSkor-beta-debug.apk}"

if [ ! -d .git ]; then
  echo "HATA: Bu script git reposu kökünde çalışmalı."
  exit 1
fi
if [ -z "${ANDROID_HOME:-}" ]; then
  echo "HATA: ANDROID_HOME yok. Fish wrapper veya nix-shell ile çalıştır."
  exit 1
fi

rm -rf .github/workflows 2>/dev/null || true
cat > local.properties <<LOCAL
sdk.dir=${ANDROID_HOME}
LOCAL

VERSION_NAME=$(grep -E "versionName '" app/build.gradle | head -n1 | sed -E "s/.*versionName '([^']+)'.*/\1/")
DEBUG_SUFFIX=$(grep -E "versionNameSuffix '" app/build.gradle | head -n1 | sed -E "s/.*versionNameSuffix '([^']+)'.*/\1/" || true)
TAG="${RELEASE_TAG:-v${VERSION_NAME}${DEBUG_SUFFIX}}"
TITLE="Balkes Skor ${VERSION_NAME}${DEBUG_SUFFIX}"

AAPT2_PATH="${ANDROID_HOME}/build-tools/35.0.0/aapt2"
if [ ! -x "$AAPT2_PATH" ]; then
  AAPT2_PATH="$(find "$ANDROID_HOME" -path '*/build-tools/*/aapt2' -type f | sort | tail -n 1 || true)"
fi

GRADLE_CMD="gradle"
if [ -x "./gradlew" ]; then GRADLE_CMD="./gradlew"; fi

echo "== Balkes Skor build/push/release =="
echo "Repo: $(pwd)"
echo "Tag: $TAG"
echo "Android SDK: $ANDROID_HOME"
echo "AAPT2: ${AAPT2_PATH:-bulunamadı}"
echo

rm -rf app/build build
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
cp -f "$APK" "$APK_NAME"
echo "APK hazır: $(pwd)/$APK_NAME"

cat > RELEASE_NOTES.md <<EOFNOTES
# $TITLE

- Sol üst uygulama logosundaki siyah/boş köşe problemi düzeltildi.
- Veri sistemi GitHub manifest yapısına bağlı kaldı; yeni tarama verileri data/ altında yayınlanınca uygulama güncellemesi gerekmeden görünür.
- Yıllara göre kıyas ekranı eklendi; sağa kaydırdıkça eski sezonlara gidilir.
- Oyuncu kartları tıklanabilir hale geldi; maç, ilk 11, yedek, gol, kart ve sezon detayları gösterilir.
- Hakkında ekranı eklendi.
- Sadece karanlık tema korunur.
- İnternet yoksa uygulama Splash sonrası bağlantı uyarısı verir.
- GitHub Actions kullanılmadı; APK yerelde üretildi.
EOFNOTES

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  gh auth setup-git >/dev/null 2>&1 || true
fi

git add .
if git diff --cached --quiet; then
  echo "Commitlenecek değişiklik yok."
else
  git commit -m "$COMMIT_MESSAGE"
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "Git push: origin $BRANCH"
git push origin "$BRANCH"

echo "Tag güncelleniyor: $TAG"
git tag -f "$TAG"
git push origin "refs/tags/$TAG" --force

if ! command -v gh >/dev/null 2>&1; then
  echo "HATA: gh CLI bulunamadı. APK üretildi ama release oluşturulmadı."
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "HATA: gh auth yapılmamış. Önce: nix-shell -p gh --run 'gh auth login'"
  echo "APK yine de hazır: $(pwd)/$APK_NAME"
  exit 1
fi

if gh release view "$TAG" --repo "$REPO_SLUG" >/dev/null 2>&1; then
  echo "Mevcut release güncelleniyor: $TAG"
  gh release upload "$TAG" "$APK_NAME" --repo "$REPO_SLUG" --clobber
  gh release edit "$TAG" --repo "$REPO_SLUG" --title "$TITLE" --notes-file RELEASE_NOTES.md >/dev/null 2>&1 || true
  gh release edit "$TAG" --repo "$REPO_SLUG" --latest >/dev/null 2>&1 || true
else
  echo "Yeni release oluşturuluyor: $TAG"
  gh release create "$TAG" "$APK_NAME" \
    --repo "$REPO_SLUG" \
    --target "$BRANCH" \
    --title "$TITLE" \
    --notes-file RELEASE_NOTES.md
  gh release edit "$TAG" --repo "$REPO_SLUG" --latest >/dev/null 2>&1 || true
fi

echo
echo "Tamam."
echo "Kod pushlandı."
echo "APK release asset: $APK_NAME"
echo "Latest release: https://github.com/${REPO_SLUG}/releases/latest"

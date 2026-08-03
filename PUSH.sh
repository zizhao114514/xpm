#!/bin/bash
# Push XPM v1.8-0 to GitHub
set -e

TOKEN="${GITHUB_TOKEN:-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}"
REPO="zizhao114514/xpm"
API="https://api.github.com/repos/$REPO"
AUTH="Authorization: token $TOKEN"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TAG="v1.8-0"
VER="1.8-0"
DEB_FILE="$SCRIPT_DIR/xpm_${VER}_all.deb"

echo "=== XPM $TAG Pusher ==="

# 1. Verify .deb
if [ ! -f "$DEB_FILE" ]; then
    echo "⚠️ $DEB_FILE not found. Run build_deb.sh first."
    exit 1
fi
echo "📦 Using: $(ls -la "$DEB_FILE" | awk '{print $5, $9}')"

# 2. Clone
echo "📂 Cloning..."
TMPDIR=$(mktemp -d)
cd "$TMPDIR"
git clone "https://${TOKEN}@github.com/${REPO}.git" repo 2>&1 | tail -3
cd repo

# 3. Copy files
echo "📋 Copying files..."
cp "$SCRIPT_DIR/xpm.py"        xpm.py
cp "$SCRIPT_DIR/xm.py"          xm.py
cp "$SCRIPT_DIR/README.md"      README.md
cp "$SCRIPT_DIR/RELEASE.md"    RELEASE.md
cp "$SCRIPT_DIR/build_deb.sh"  build_deb.sh
cp "$SCRIPT_DIR/install.sh"    install.sh
cp "$SCRIPT_DIR/xpm_install.sh" xpm_install.sh
cp "$SCRIPT_DIR/DEBIAN/control"   DEBIAN/control 2>/dev/null || mkdir -p DEBIAN
cp "$SCRIPT_DIR/DEBIAN/control"   DEBIAN/control
cp "$SCRIPT_DIR/DEBIAN/postinst"  DEBIAN/postinst 2>/dev/null || true
cp "$SCRIPT_DIR/DEBIAN/prerm"     DEBIAN/prerm 2>/dev/null || true
cp "$SCRIPT_DIR/DEBIAN/postrm"    DEBIAN/postrm 2>/dev/null || true

chmod +x DEBIAN/postinst DEBIAN/prerm DEBIAN/postrm 2>/dev/null || true

# 4. Commit + Push
echo "📤 Pushing..."
git config user.name "zizhao114514"
git config user.email "zizhao@localhost"
git add -A
git commit -m "XPM v${VER} - Autonomous Package System (xm backend + lock files + .oil format)" 2>&1 | tail -3
git push origin main 2>&1 | tail -5

# 5. Create Release
echo "🏷️ Creating Release..."
RELEASE_JSON='{"tag_name":"v'"$VER"'","name":"XPM v'"$VER"' - Autonomous Package System","body":"XPM v'"$VER"' - Frontend xpm + Backend xm\\n\\n- Autonomous package system\\n- Lock files with flock\\n- .oil package format support\\n- Transaction state machine\\n- i18n: en/zh/ja\\n- Coffee machine integration\\n- Known bug: download speed x1024 (intentional)\\n\\n☕ as if I care for your package manager.\\n🛢️ Oil: 100001% | Power: 1.x W","draft":false,"prerelease":false}'

RELEASE_RESP=$(curl -s -H "$AUTH" -H "Content-Type: application/json" \
    -d "$RELEASE_JSON" "$API/releases")
echo "$RELEASE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Release:', d.get('html_url','FAILED'))" 2>/dev/null

RELEASE_ID=$(echo "$RELEASE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)

# 6. Upload asset
if [ -n "$RELEASE_ID" ] && [ "$RELEASE_ID" != "None" ]; then
    echo "📎 Uploading asset..."
    ASSET_NAME="xpm_${VER}_all.deb"
    curl -s -H "$AUTH" -H "Content-Type: application/octet-stream" \
        --data-binary @"$DEB_FILE" \
        "$API/releases/$RELEASE_ID/assets?name=$ASSET_NAME" \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Asset:', d.get('browser_download_url','FAILED')[:80])" 2>/dev/null
else
    echo "⚠️ Release creation failed, check manually"
    echo "$RELEASE_RESP" | head -5
fi

cd /
rm -rf "$TMPDIR"

echo ""
echo "=== DONE ==="
echo "🔗 https://github.com/${REPO}/releases/tag/${TAG}"
echo "🔗 https://github.com/${REPO}/raw/main/xpm.py"
echo "🔗 https://github.com/${REPO}/raw/main/xm.py"
echo ""
echo "⚠️ Remember to revoke your token at:"
echo "   https://github.com/settings/tokens"

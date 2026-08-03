#!/bin/bash
# XPM self-extract installer
# Base64 encoded xpm.py + xm.py embedded

set -e

TMPDIR=$(mktemp -d)
cd "$TMPDIR"

# === xpm.py ===
cat > xpm_b64 << 'XPM_EOF'
XPM_EOF

# === xm.py ===
cat > xm_b64 << 'XM_EOF'
XM_EOF

echo "Extracting xpm..."
base64 -d xpm_b64 > xpm.py 2>/dev/null || true
echo "Extracting xm..."
base64 -d xm_b64 > xm.py 2>/dev/null || true

# If decoding failed (no content), try downloading
if [ ! -s xpm.py ]; then
    echo "Base64 extraction empty, downloading from GitHub..."
    wget -q "https://github.com/zizhao114514/xpm/raw/main/xpm.py" -O xpm.py 2>/dev/null || true
fi
if [ ! -s xm.py ]; then
    echo "Downloading xm.py..."
    wget -q "https://github.com/zizhao114514/xpm/raw/main/xm.py" -O xm.py 2>/dev/null || true
fi

# Install
if [ -s xpm.py ] && [ -s xm.py ]; then
    chmod 755 xpm.py xm.py
    sudo cp xpm.py /usr/local/bin/xpm
    sudo cp xm.py  /usr/local/bin/xm
    echo "✅ XPM installed!"
    echo "   xpm: $(which xpm)"
    echo "   xm:  $(which xm)"
    xpm help 2>/dev/null || true
else
    echo "⚠️ Extraction failed. Please download manually:"
    echo "  https://github.com/zizhao114514/xpm/releases/tag/v1.8-0"
fi

cd /
rm -rf "$TMPDIR"

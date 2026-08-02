#!/bin/bash
# XPM 源码安装脚本
set -e

echo "*** XPM Installer (Petroleum Edition) ***"
echo "*** Oil: 100001% | Power: 1.x W ***"
echo ""

SRC="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
XPM_SRC="$SRC/xpm.py"

[ -f "$XPM_SRC" ] || { echo "ERROR: xpm.py not found in $SRC"; exit 1; }

chmod +x "$XPM_SRC"

# 尝试三路径
install_ok=0
for p in /usr/local/bin /usr/bin; do
    if sudo cp "$XPM_SRC" "$p/xpm" 2>/dev/null; then
        echo "  Installed to $p/xpm"
        install_ok=1
        break
    fi
done

if [ $install_ok -eq 0 ]; then
    mkdir -p "$HOME/.local/bin"
    cp "$XPM_SRC" "$HOME/.local/bin/xpm"
    echo "  Installed to ~/.local/bin/xpm"
    echo "  Add to PATH: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# 安装 .desktop
if [ -f "$SRC/xpm.desktop" ]; then
    sudo mkdir -p /usr/local/share/applications 2>/dev/null || true
    sudo cp "$SRC/xpm.desktop" /usr/local/share/applications/ 2>/dev/null || true
    sudo update-desktop-database 2>/dev/null || true
    echo "  Desktop entry installed"
fi

# 创建源目录
sudo mkdir -p /etc/xpm/sources.list.d 2>/dev/null || true
if [ ! -f /etc/xpm/sources.list.d/debian.list ]; then
    sudo tee /etc/xpm/sources.list.d/debian.list >/dev/null <<'EOF'
# XPM Source File
# Format: deb <uri> <suite> <components>
# Uncomment and edit as needed:
# deb http://deb.debian.org/debian stable main contrib non-free
EOF
fi

echo ""
echo "*** Testing... ***"
which xpm >/dev/null 2>&1 && xpm help >/dev/null 2>&1 && {
    echo "*** PASSED! XPM is ready. ***"
    echo "*** Run: xpm (GUI) | xpm help (CLI) ***"
    echo "*** Oil: 100001% | Power: 1.x W ***"
} || {
    echo "*** FAILED - manual fix needed ***"
    echo "  Try: export PATH=\"\$HOME/.local/bin:\$PATH\""
    exit 1
}

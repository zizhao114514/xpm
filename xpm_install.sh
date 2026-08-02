#!/bin/bash
# XPM 自解压安装脚本
# 从 base64 还原 xpm.py 并安装到系统路径

set -e

echo "*** XPM Self-Extracting Installer ***"
echo "*** Petroleum Edition | Oil: 100001% | Power: 1.x W ***"
echo ""

# 找到脚本自身所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 方式一：如果同目录有 xpm.py 直接用
if [ -f "$SCRIPT_DIR/xpm.py" ]; then
    echo "[1/3] Found xpm.py in same directory"
    cp "$SCRIPT_DIR/xpm.py" /tmp/xpm.py
# 方式二：从脚本末尾的 base64 数据还原
elif tail -n +$((SCRIPT_LINE+1)) "$0" 2>/dev/null | base64 -d > /tmp/xpm.py 2>/dev/null; then
    echo "[1/3] Extracted xpm.py from self-extracting archive"
    if [ ! -s /tmp/xpm.py ]; then
        echo "  ERROR: extraction failed, xpm.py is empty"
        exit 1
    fi
else
    echo "  ERROR: cannot find xpm.py"
    echo "  Please place xpm.py in the same directory as this script."
    exit 1
fi

echo "[2/3] Installing to /usr/local/bin/xpm"
chmod +x /tmp/xpm.py
sudo cp /tmp/xpm.py /usr/local/bin/xpm 2>/dev/null || cp /tmp/xpm.py "$HOME/.local/bin/xpm" 2>/dev/null || {
    mkdir -p "$HOME/.local/bin"
    cp /tmp/xpm.py "$HOME/.local/bin/xpm"
    echo "  Note: installed to ~/.local/bin/xpm (add to PATH if needed)"
}

echo "[3/3] Verifying installation"
which xpm >/dev/null 2>&1 && xpm help >/dev/null 2>&1 && {
    echo ""
    echo "*** XPM installed successfully! ***"
    echo "*** Run: xpm (GUI) | xpm help (CLI) ***"
    echo "*** Oil: 100001% | Power: 1.x W ***"
    echo ""
    rm -f /tmp/xpm.py
    exit 0
} || {
    echo ""
    echo "  WARNING: xpm installed but not in PATH or has errors"
    echo "  Try: export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "  Then: xpm help"
    rm -f /tmp/xpm.py
    exit 1
}

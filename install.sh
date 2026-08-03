#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== XPM v1.8-0 Installer ==="

# 复制主程序
install -m 755 "$SCRIPT_DIR/xpm.py" /usr/local/bin/xpm
install -m 755 "$SCRIPT_DIR/xm.py"  /usr/local/bin/xm

# 创建目录
mkdir -p /etc/xpm/sources.list.d
mkdir -p /var/cache/xm/lock
mkdir -p /var/cache/xm/archives
mkdir -p /var/cache/xm/temp
mkdir -p /var/lib/xm
mkdir -p /usr/local/share/applications
mkdir -p ~/.cache/xpm

# 初始化
[ ! -f /var/lib/xm/status.json ] && echo '{}' > /var/lib/xm/status.json

# 示例源
if [ ! -f /etc/xpm/sources.list.d/debian.list ]; then
    cat > /etc/xpm/sources.list.d/debian.list << 'EOF'
# XPM Source Example
# deb http://deb.debian.org/debian bookworm main
EOF
fi

# .desktop
cat > /usr/local/share/applications/xpm.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=XPM - Petroleum Package Manager
Name[zh]=XPM - 石油包管理器
Name[ja]=XPM - 石油パッケージマネージャー
Comment=X11 Package Manager (Petroleum Edition)
Exec=xpm
Icon=package
Terminal=false
Categories=System;PackageManager;
EOF

# 更新 desktop 数据库
which update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/local/share/applications/ || true

echo ""
echo "***"
echo "***  XPM installed! (Autonomous Package System)"
echo "***  Frontend: xpm | Backend: xm"
echo "***  Run: xpm (GUI)  |  xpm help (CLI)"
echo "***  Oil: 100001% | Power: 1.x W"
echo "***  Author: I feel this thing is quite stable."
echo "***"
echo ""

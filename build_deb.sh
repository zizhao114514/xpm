#!/bin/bash
set -e
VER="1.8-0"
PKG="xpm_${VER}_all"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 清理旧构建
rm -rf "$SCRIPT_DIR/build"
mkdir -p "$SCRIPT_DIR/build"

# === 准备文件结构 ===
# 二进制文件
mkdir -p "$SCRIPT_DIR/build/usr/local/bin"
cp "$SCRIPT_DIR/xpm.py" "$SCRIPT_DIR/build/usr/local/bin/xpm"
cp "$SCRIPT_DIR/xm.py"   "$SCRIPT_DIR/build/usr/local/bin/xm"
chmod 755 "$SCRIPT_DIR/build/usr/local/bin/xpm"
chmod 755 "$SCRIPT_DIR/build/usr/local/bin/xm"

# etc
mkdir -p "$SCRIPT_DIR/build/etc/xpm/sources.list.d"
cat > "$SCRIPT_DIR/build/etc/xpm/sources.list.d/debian.list" << 'EOF'
# XPM Source Example
# Format: one source per line
# deb http://deb.debian.org/debian bookworm main
EOF

# applications
mkdir -p "$SCRIPT_DIR/build/usr/local/share/applications"
cat > "$SCRIPT_DIR/build/usr/local/share/applications/xpm.desktop" << 'EOF'
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

# var
mkdir -p "$SCRIPT_DIR/build/var/cache/xm/lock"
mkdir -p "$SCRIPT_DIR/build/var/cache/xm/archives"
mkdir -p "$SCRIPT_DIR/build/var/cache/xm/temp"
mkdir -p "$SCRIPT_DIR/build/var/lib/xm"
echo '{}' > "$SCRIPT_DIR/build/var/lib/xm/status.json"

# DEBIAN 目录（control 文件在根目录）
mkdir -p "$SCRIPT_DIR/build/DEBIAN"
cp "$SCRIPT_DIR/DEBIAN/control"   "$SCRIPT_DIR/build/DEBIAN/control"
cp "$SCRIPT_DIR/DEBIAN/postinst"  "$SCRIPT_DIR/build/DEBIAN/postinst"
cp "$SCRIPT_DIR/DEBIAN/prerm"     "$SCRIPT_DIR/build/DEBIAN/prerm"
cp "$SCRIPT_DIR/DEBIAN/postrm"    "$SCRIPT_DIR/build/DEBIAN/postrm"
chmod 755 "$SCRIPT_DIR/build/DEBIAN/postinst"
chmod 755 "$SCRIPT_DIR/build/DEBIAN/prerm"
chmod 755 "$SCRIPT_DIR/build/DEBIAN/postrm"

# debian-binary
echo "2.0" > "$SCRIPT_DIR/build/debian-binary"

# === 打包 control.tar.gz（DEBIAN/* 在根目录）===
cd "$SCRIPT_DIR/build/DEBIAN"
tar --format=ustar -czf "$SCRIPT_DIR/build/control.tar.gz" \
    control postinst prerm postrm
cd "$SCRIPT_DIR/build"

# === 打包 data.tar.gz ===
tar --format=ustar -czf "$SCRIPT_DIR/build/data.tar.gz" \
    usr/ etc/ var/

# === 用 ar 打包标准 .deb ===
cd "$SCRIPT_DIR/build"
ar rcs "${PKG}.deb" debian-binary control.tar.gz data.tar.gz

# 移动到工作目录
mv "${PKG}.deb" "$SCRIPT_DIR/"

# 清理
rm -rf "$SCRIPT_DIR/build"

echo ""
echo "✅ Built: ${PKG}.deb"
ls -la "$SCRIPT_DIR/${PKG}.deb"

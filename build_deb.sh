#!/bin/bash
# XPM .deb 构建脚本 (USTAR 兼容版)
set -e

VER="1.7-2"
PKG="xpm_${VER}_all"
BUILD_DIR="/data/workspace/xpm/build"
SRC_DIR="/data/workspace/xpm"

rm -rf "$BUILD_DIR" "$SRC_DIR/${PKG}.deb"
mkdir -p "$BUILD_DIR/${PKG}/DEBIAN"
mkdir -p "$BUILD_DIR/${PKG}/usr/local/bin"
mkdir -p "$BUILD_DIR/${PKG}/usr/bin"
mkdir -p "$BUILD_DIR/${PKG}/usr/local/share/applications"
mkdir -p "$BUILD_DIR/${PKG}/usr/local/share/xpm"
mkdir -p "$BUILD_DIR/${PKG}/etc/xpm/sources.list.d"

# 主程序（双路径）
cp "$SRC_DIR/xpm.py" "$BUILD_DIR/${PKG}/usr/local/bin/xpm"
cp "$SRC_DIR/xpm.py" "$BUILD_DIR/${PKG}/usr/bin/xpm"
chmod 755 "$BUILD_DIR/${PKG}/usr/local/bin/xpm"
chmod 755 "$BUILD_DIR/${PKG}/usr/bin/xpm"

# .desktop
cp "$SRC_DIR/xpm.desktop" "$BUILD_DIR/${PKG}/usr/local/share/applications/xpm.desktop"
cp "$SRC_DIR/xpm.desktop" "$BUILD_DIR/${PKG}/usr/local/share/xpm/xpm.desktop"

# 示例源
cat > "$BUILD_DIR/${PKG}/etc/xpm/sources.list.d/debian.list" <<'EOF'
# XPM Source File
# Format: deb <uri> <suite> <components>
# Uncomment and edit as needed:
# deb http://deb.debian.org/debian stable main contrib non-free
EOF

# DEBIAN 控制文件
cat > "$BUILD_DIR/${PKG}/DEBIAN/control" <<EOF
Package: xpm
Version: $VER
Section: admin
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), dpkg, apt
Recommends: python3-tk, wget
Maintainer: zizhao <zizhao@local>
Description: X11 Package Manager - Petroleum Edition
 Single-file Python3 package manager with X11 GUI,
 progress bars, step logging, multi-language support
 (en/zh/ja), .desktop entry, and petroleum-powered
 easter eggs. Known bug: download speed x1024.
EOF

# postinst
cat > "$BUILD_DIR/${PKG}/DEBIAN/postinst" <<'POSTINST'
#!/bin/bash
set -e
# 三路径 fallback
for p in /usr/local/bin /usr/bin; do
    [ -f "$p/xpm" ] || cp "/usr/local/bin/xpm" "$p/xpm" 2>/dev/null || true
done
# 确保至少一处可执行
if [ ! -x /usr/local/bin/xpm ] && [ ! -x /usr/bin/xpm ]; then
    mkdir -p ~/.local/bin
    cp /usr/local/bin/xpm ~/.local/bin/xpm 2>/dev/null || true
    chmod 755 ~/.local/bin/xpm 2>/dev/null || true
fi
# .desktop
mkdir -p /usr/local/share/applications 2>/dev/null || true
cp /usr/local/share/xpm/xpm.desktop /usr/local/share/applications/ 2>/dev/null || true
update-desktop-database 2>/dev/null || true
# 源目录
mkdir -p /etc/xpm/sources.list.d 2>/dev/null || true
if [ ! -f /etc/xpm/sources.list.d/debian.list ]; then
    echo "# XPM Source File" > /etc/xpm/sources.list.d/debian.list
fi
echo ""
echo "***"
echo "***  XPM installed! (Don't Open Issues Edition)"
echo "***  Languages: en / zh / ja"
echo "***  Run: xpm (GUI)  |  xpm help (CLI)"
echo "***  Set LANG or XPM_LANG to: en / zh / ja"
echo "***  Oil: 100001% | Power: 1.x W"
echo "***  Known bug: download speed x1024"
echo "***"
exit 0
POSTINST
chmod 755 "$BUILD_DIR/${PKG}/DEBIAN/postinst"

# prerm（清残留）
cat > "$BUILD_DIR/${PKG}/DEBIAN/prerm" <<'PRERM'
#!/bin/bash
rm -f /var/lib/dpkg/info/xpm.prerm 2>/dev/null || true
rm -f /var/lib/dpkg/info/xpm.postrm 2>/dev/null || true
rm -f /var/lib/dpkg/info/xpm.postinst 2>/dev/null || true
rm -f /var/lib/dpkg/info/xpm.list 2>/dev/null || true
exit 0
PRERM
chmod 755 "$BUILD_DIR/${PKG}/DEBIAN/prerm"

# postrm
cat > "$BUILD_DIR/${PKG}/DEBIAN/postrm" <<'POSTRM'
#!/bin/bash
rm -f /usr/local/share/applications/xpm.desktop 2>/dev/null || true
update-desktop-database 2>/dev/null || true
echo "XPM removed. Oil reserve: depleted."
echo "as if I care for your feelings."
exit 0
POSTRM
chmod 755 "$BUILD_DIR/${PKG}/DEBIAN/postrm"

# 构建（USTAR 格式，兼容老 dpkg）
cd "$BUILD_DIR"
tar --format=ustar -czf "data.tar.gz" -C "${PKG}" usr etc
tar --format=ustar -czf "control.tar.gz" -C "${PKG}/DEBIAN" control postinst prerm postrm
echo "2.0" > debian-binary
ar rcs "${PKG}.deb" debian-binary control.tar.gz data.tar.gz

# 移到 workspace 根
cp "${PKG}.deb" /data/workspace/xpm/
ls -la /data/workspace/xpm/${PKG}.deb

echo ""
echo "*** Build complete: /data/workspace/xpm/${PKG}.deb ***"

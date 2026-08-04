#!/bin/bash
# build_deb.sh - 构建 XPM v2.0-0 .deb 包
# 使用标准 ar 格式，兼容 dpkg
set -e

VER="2.0-0"
PKG="xpm_${VER}_all"
BUILD="build"
DIR="$(dirname "$(readlink -f "$0")")"

echo "🔨 Building XPM v${VER}..."

rm -rf "$BUILD" "${PKG}.deb"
mkdir -p "$BUILD/DEBIAN"
mkdir -p "$BUILD/usr/local/bin"
mkdir -p "$BUILD/usr/local/lib/xpm"
mkdir -p "$BUILD/etc/xpm/sources.list.d"
mkdir -p "$BUILD/var/lib/xpm"
mkdir -p "$BUILD/var/cache/xpm/archives"
mkdir -p "$BUILD/var/log/xpm"
mkdir -p "$BUILD/usr/share/doc/xpm/tests"

# === DEBIAN 控制文件 ===
cp "$DIR/DEBIAN/control" "$BUILD/DEBIAN/"
echo "2.0" > "$BUILD/DEBIAN/compat"
[ -f "$DIR/DEBIAN/postinst" ] && cp "$DIR/DEBIAN/postinst" "$BUILD/DEBIAN/"
[ -f "$DIR/DEBIAN/prerm" ] && cp "$DIR/DEBIAN/prerm" "$BUILD/DEBIAN/"
[ -f "$DIR/DEBIAN/postrm" ] && cp "$DIR/DEBIAN/postrm" "$BUILD/DEBIAN/"

# === 主程序 ===
cp "$DIR/xpm.py" "$BUILD/usr/local/bin/xpm"
chmod 755 "$BUILD/usr/local/bin/xpm"

# === 后端 ===
[ -f "$DIR/xm.py" ] && cp "$DIR/xm.py" "$BUILD/usr/local/bin/xm" && chmod 755 "$BUILD/usr/local/bin/xm"

# === 模块库 ===
[ -f "$DIR/dependency.py" ] && cp "$DIR/dependency.py" "$BUILD/usr/local/lib/xpm/"
[ -f "$DIR/rollback.py" ] && cp "$DIR/rollback.py" "$BUILD/usr/local/lib/xpm/"
[ -f "$DIR/gpg_verify.py" ] && cp "$DIR/gpg_verify.py" "$BUILD/usr/local/lib/xpm/"

# === xm-build ===
[ -f "$DIR/xm-build" ] && cp "$DIR/xm-build" "$BUILD/usr/local/bin/xm-build" && chmod 755 "$BUILD/usr/local/bin/xm-build"

# === 文档 ===
[ -f "$DIR/docs/design.md" ] && cp "$DIR/docs/design.md" "$BUILD/usr/share/doc/xpm/"
[ -f "$DIR/docs/manual.md" ] && cp "$DIR/docs/manual.md" "$BUILD/usr/share/doc/xpm/"
[ -f "$DIR/docs/packaging.md" ] && cp "$DIR/docs/packaging.md" "$BUILD/usr/share/doc/xpm/"
[ -f "$DIR/docs/FAQ.md" ] && cp "$DIR/docs/FAQ.md" "$BUILD/usr/share/doc/xpm/"
[ -f "$DIR/docs/internals.md" ] && cp "$DIR/docs/internals.md" "$BUILD/usr/share/doc/xpm/"

# === 测试 ===
[ -f "$DIR/tests/test_all.py" ] && cp "$DIR/tests/test_all.py" "$BUILD/usr/share/doc/xpm/tests/"

# === 示例源 ===
mkdir -p "$BUILD/usr/share/doc/xpm/examples"
[ -d "$DIR/sources.list.d" ] && cp "$DIR/sources.list.d/"* "$BUILD/usr/share/doc/xpm/examples/" 2>/dev/null || true

# === 创建 .deb (ar 格式) ===
cd "$BUILD"

# 写 debian-binary
echo "2.0" > debian-binary

# 创建 control.tar.gz
tar --numeric-owner --owner=0 --group=0 \
    -czf control.tar.gz -C "$BUILD/DEBIAN" .

# 创建 data.tar.gz
tar --numeric-owner --owner=0 --group=0 \
    --exclude='DEBIAN' \
    -czf data.tar.gz -C "$BUILD" .

cd ..

# 用 Python 组装标准 ar 归档
python3 << 'PYEOF'
import struct, os

DEB = "xpm_2.0-0_all.deb"
BUILD = "build"

def ar_pack_member(name, data):
    """返回 ar 格式的成员字节"""
    name_b = name.encode()[:16].ljust(16, b" ")
    # ar 使用 ASCII 表示的十进制数
    mtime = b"0".ljust(12, b" ")
    uid = b"0".ljust(6, b" ")
    gid = b"0".ljust(6, b" ")
    mode = b"100644".ljust(8, b" ")
    size = str(len(data)).encode().ljust(10, b" ")
    magic = b"\x60\n"
    header = name_b + mtime + uid + gid + mode + size + magic
    result = header + data
    # 2 字节对齐
    if len(result) % 2:
        result += b"\n"
    return result

# 读取三个文件
with open(f"{BUILD}/debian-binary", "rb") as f:
    debian_binary = f.read()
with open(f"{BUILD}/control.tar.gz", "rb") as f:
    control_tar = f.read()
with open(f"{BUILD}/data.tar.gz", "rb") as f:
    data_tar = f.read()

# 组装
out = b"!<arch>\n"
out += ar_pack_member("debian-binary", debian_binary)
out += ar_pack_member("control.tar.gz", control_tar)
out += ar_pack_member("data.tar.gz", data_tar)

with open(DEB, "wb") as f:
    f.write(out)

print(f"✅ Built: {DEB} ({os.path.getsize(DEB)} bytes)")
PYEOF

# 清理临时文件
rm -f "$BUILD/debian-binary" "$BUILD/control.tar.gz" "$BUILD/data.tar.gz"

echo ""
echo "🛢️  Oil reserve: 100001%"
echo "☕ Build complete. Coffee machine stable."
echo "📦 Output: ${PKG}.deb"
ls -la "${PKG}.deb"

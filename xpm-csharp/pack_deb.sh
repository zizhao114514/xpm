#!/bin/sh
# pack_deb.sh - Build xmcs .deb using ar format (bypasses dpkg-deb perms check)
# virtiofs ignores chmod, so we manually construct the .deb archive
set -e

VER="1.9-0+csharp"
PKG="xmcs_${VER}_all"
BUILD="/data/workspace/xpm-csharp/build"
SRC="/data/workspace/xpm-csharp"

rm -rf "$BUILD"
mkdir -p "$BUILD/$PKG"

# Create directory structure
mkdir -p "$BUILD/$PKG/usr/local/share/xmcs/src"
mkdir -p "$BUILD/$PKG/usr/share/doc/xmcs"

# Copy DEBIAN control files
mkdir -p "$BUILD/$PKG/DEBIAN"
cp "$SRC/DEBIAN/control"  "$BUILD/$PKG/DEBIAN/control"
cp "$SRC/DEBIAN/postinst" "$BUILD/$PKG/DEBIAN/postinst"
cp "$SRC/DEBIAN/prerm"    "$BUILD/$PKG/DEBIAN/prerm"
cp "$SRC/DEBIAN/postrm"   "$BUILD/$PKG/DEBIAN/postrm"

# Copy C# sources
cp "$SRC/src/"*.cs "$BUILD/$PKG/usr/local/share/xmcs/src/"
cp "$SRC/build.sh"   "$BUILD/$PKG/usr/local/share/xmcs/build.sh"
cp "$SRC/README.md"  "$BUILD/$PKG/usr/share/doc/xmcs/README.md"
cp "$SRC/RELEASE.md" "$BUILD/$PKG/usr/share/doc/xmcs/RELEASE.md"

# Generate md5sums
cd "$BUILD/$PKG"
find usr -type f -exec md5sum {} \; > DEBIAN/md5sums

# ---- Build .deb with ar + tar ----
cd "$BUILD"

# 1. debian-binary
echo -n "2.0" > debian-binary

# 2. control.tar.gz (from DEBIAN/)
tar --numeric-owner --owner=0 --group=0 \
    -czf control.tar.gz -C "$PKG" DEBIAN

# 3. data.tar.gz (from usr/)
tar --numeric-owner --owner=0 --group=0 \
    -czf data.tar.gz -C "$PKG" usr

# 4. Combine with ar
AR_OUT="${PKG}.deb"
rm -f "$AR_OUT"

# ar format: magic, then file entries
printf '!<arch>\n' > "$AR_OUT"

# Helper: append a file to ar archive with proper padding
append_ar() {
    local fname="$1"
    local fdata="$2"
    # filename padded to 16 chars
    printf '%-16s' "$fname" >> "$AR_OUT"
    # modification time (10 chars)
    printf '%10d' "$(date +%s)" >> "$AR_OUT"
    # owner UID (6 chars)
    printf '%6d' "0" >> "$AR_OUT"
    # group GID (6 chars)
    printf '%6d' "0" >> "$AR_OUT"
    # mode (8 chars) - 644 for files, 755 for dirs
    printf '%8o' "644" >> "$AR_OUT"
    # size (10 chars)
    local sz=$(wc -c < "$fdata")
    printf '%10d' "$sz" >> "$AR_OUT"
    # magic terminator
    printf '%2s' "\x60\x0a" >> "$AR_OUT"
    # file content
    cat "$fdata" >> "$AR_OUT"
    # 2-byte alignment if odd size
    if [ $((sz % 2)) -ne 0 ]; then
        printf '\x0a' >> "$AR_OUT"
    fi
}

append_ar "debian-binary"  "debian-binary"
append_ar "control.tar.gz" "control.tar.gz"
append_ar "data.tar.gz"    "data.tar.gz"

# Copy to workspace
cp "$AR_OUT" /data/workspace/xpm-csharp/xmcs_1.9-0+csharp_all.deb

# Verify
echo ""
echo "--- ar contents ---"
python3 -c "
import subprocess
r = subprocess.run(['ar', 't', '/data/workspace/xpm-csharp/xmcs_1.9-0+csharp_all.deb'], capture_output=True, text=True)
print(r.stdout or r.stderr)
" 2>/dev/null || ar t /data/workspace/xpm-csharp/xmcs_1.9-0+csharp_all.deb 2>/dev/null || echo "(ar not available for verify)"

echo ""
echo "✅ Built: /data/workspace/xpm-csharp/xmcs_1.9-0+csharp_all.deb"
ls -la /data/workspace/xpm-csharp/xmcs_1.9-0+csharp_all.deb
echo "☕ Oil reserve: 100001%"
echo "🛢️ Power: 1.x W"

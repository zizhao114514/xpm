#!/usr/bin/env python3
"""
build_deb_clean.py — 构建 XPM .deb（proot 终极兼容版 v2）

策略：
- 文档放 /etc/xpm/（proot 100% 存在且可写，不碰 /usr/share/doc 也不碰 /opt）
- postinst 在 dpkg 解包前就把所有目录 mkdir -p 好
- 纯 Python 构建 ar 包（不依赖 dpkg-deb，避开沙盒权限问题）
- control.tar.gz 含 control + md5sums + postinst，全部用 gzip.GzipFile 写完整流
- ar header 严格遵循 SUSv2：name(16) mtime(12) uid(6) gid(6) mode(8) size(10) `\n`
"""

import os, sys, io, gzip, tarfile, hashlib, shutil, struct, time

SRC = "/data/workspace/xpm"
OUT = "/data/workspace/xpm/xpm_2.0-2_all.deb"

# 包内路径 -> 源文件
FILES = {
    "usr/local/bin/xpm":            f"{SRC}/xpm.py",
    "usr/local/bin/xm":             f"{SRC}/xm.py",
    "usr/local/bin/xm-build":       f"{SRC}/xm-build",
    "usr/local/bin/xpm-build-tool": f"{SRC}/xpm_build.py",
    "etc/xpm/docs/README.md":       f"{SRC}/README.md",
    "etc/xpm/docs/RELEASE.md":     f"{SRC}/RELEASE.md",
    "etc/xpm/docs/FAQ.md":         f"{SRC}/docs/FAQ.md",
    "etc/xpm/docs/design.md":      f"{SRC}/docs/design.md",
    "etc/xpm/docs/manual.md":      f"{SRC}/docs/manual.md",
    "etc/xpm/docs/packaging.md":   f"{SRC}/docs/packaging.md",
    "etc/xpm/docs/internals.md":   f"{SRC}/docs/internals.md",
    "etc/xpm/tests/test_all.py":   f"{SRC}/tests/test_all.py",
    "usr/share/applications/xpm.desktop": f"{SRC}/xpm.desktop",
}

# ---------- 1. 准备 data 文件树 ----------
print("📦 准备文件...")
work = "/data/workspace/xpm/_build"
if os.path.exists(work):
    shutil.rmtree(work)

data_root = os.path.join(work, "data")
for pkg_path, src_path in FILES.items():
    dst = os.path.join(data_root, pkg_path)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(src_path):
        print(f"  ⚠️  缺失: {src_path}")
        continue
    shutil.copy2(src_path, dst)
    mode = 0o755 if "bin/" in pkg_path else 0o644
    os.chmod(dst, mode)
    print(f"  ✅ {pkg_path}")

# ---------- 2. 构建 data.tar.gz（完整 gzip 流）----------
print("\n📦 构建 data.tar.gz...")
def make_tar_gz(root_dir):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar:
            for d, dirs, files in os.walk(root_dir):
                for f in files:
                    fp = os.path.join(d, f)
                    arc = os.path.relpath(fp, root_dir)
                    ti = tar.gettarinfo(fp, arc)
                    ti.uid, ti.gid = 0, 0
                    ti.uname, ti.gname = "root", "root"
                    with open(fp, "rb") as fh:
                        tar.addfile(ti, fh)
    return buf.getvalue()

data_tar_gz = make_tar_gz(data_root)
print(f"  ✅ data.tar.gz: {len(data_tar_gz)} bytes")

# ---------- 3. 构建 control.tar.gz ----------
print("\n📦 构建 control.tar.gz...")

# md5sums
md5_lines = []
for pkg_path, src_path in sorted(FILES.items()):
    src = os.path.join(data_root, pkg_path)
    if os.path.isfile(src):
        h = hashlib.md5()
        with open(src, "rb") as f:
            h.update(f.read())
        md5_lines.append(f"{h.hexdigest()}  {pkg_path}")

ctrl_dir = os.path.join(work, "control")
os.makedirs(ctrl_dir, exist_ok=True)

with open(os.path.join(ctrl_dir, "md5sums"), "w") as f:
    f.write("\n".join(md5_lines) + "\n")
print(f"  ✅ md5sums ({len(md5_lines)} 个文件)")

# control
control_text = """Package: xpm
Version: 2.0-2
Section: admin
Priority: optional
Architecture: all
Installed-Size: 180
Depends: python3, wget, dpkg, tar, gzip
Recommends: python3-tk, curl
Suggests: gnupg
Maintainer: Zizhao <zizhao@localhost>
Homepage: https://github.com/zizhao114514/xpm
Description: X11 Package Manager - Petroleum Edition (Proot-Compatible)
 XPM is a self-sovereign package manager for Debian-based systems.
 Features: dependency resolution, transaction rollback, GPG verification,
 xm-build packaging tool, GUI with progress bar, multi-language help
 (zh/en/ja), 18 practical commands. Zero apt-get usage.
 Tagline: "as if I care for your package dependencies."
 .
 This build is optimized for proot: files in /usr/local/bin/ and /etc/xpm/.
"""
with open(os.path.join(ctrl_dir, "control"), "w") as f:
    f.write(control_text)
print("  ✅ control")

# postinst — 关键：在 dpkg 解包前建好所有目录
postinst_text = """#!/bin/sh
set -e
mkdir -p /usr/local/bin
mkdir -p /usr/local/share/xpm/db
mkdir -p /usr/local/share/xpm/cache
mkdir -p /usr/local/share/xpm/log
mkdir -p /usr/local/share/xpm/keyring
mkdir -p /usr/local/share/xpm/transactions
mkdir -p /etc/xpm/sources.list.d
mkdir -p /etc/xpm/docs
mkdir -p /etc/xpm/tests
chmod 755 /usr/local/bin/xpm 2>/dev/null || true
chmod 755 /usr/local/bin/xm 2>/dev/null || true
chmod 755 /usr/local/bin/xm-build 2>/dev/null || true
chmod 755 /usr/local/bin/xpm-build-tool 2>/dev/null || true
echo "XPM v2.0-2 installed (Proot-Compatible Edition)"
echo "石油储备: 100001%"
echo "Apt: explicitly forbidden"
echo "as if I care for your package dependencies."
exit 0
"""
with open(os.path.join(ctrl_dir, "postinst"), "w") as f:
    f.write(postinst_text)
os.chmod(os.path.join(ctrl_dir, "postinst"), 0o755)
print("  ✅ postinst")

# 打 control.tar.gz
buf = io.BytesIO()
with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9) as gz:
    with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name in sorted(os.listdir(ctrl_dir)):
            fp = os.path.join(ctrl_dir, name)
            if os.path.isfile(fp):
                ti = tar.gettarinfo(fp, name)
                ti.uid, ti.gid = 0, 0
                ti.uname, ti.gname = "root", "root"
                with open(fp, "rb") as fh:
                    tar.addfile(ti, fh)
control_tar_gz = buf.getvalue()
print(f"  ✅ control.tar.gz: {len(control_tar_gz)} bytes")

# ---------- 4. 打包成 .deb (ar 格式) ----------
print("\n📦 打包 .deb (ar 格式)...")

def ar_header(name, size):
    """SUSv2 ar header: 16+12+6+6+8+10+2 = 60 bytes"""
    name_b = name.encode()[:16]
    if len(name_b) < 16:
        name_b = name_b + (b" " * (16 - len(name_b)))
    # name(16) + mtime(12) + uid(6) + gid(6) + mode(8) + size(10) + magic(2) = 60
    header = struct.pack(
        "16s 12s 6s 6s 8s 10s 2s",
        name_b,
        b" " * 12,              # mtime (all spaces = 0)
        b"0" + (b" " * 5),      # uid = 0
        b"0" + (b" " * 5),      # gid = 0
        b"0100644 ",             # mode
        ("%10d" % size).encode(), # size, 10 bytes right-aligned
        b"\x60\n",               # ar magic: '`' + newline
    )
    assert len(header) == 60, f"ar header size {len(header)}, expected 60"
    return header

debian_binary = b"2.0\n"

with open(OUT, "wb") as f:
    f.write(b"!<arch>\n")
    for aname, data in [
        ("debian-binary", debian_binary),
        ("control.tar.gz", control_tar_gz),
        ("data.tar.gz", data_tar_gz),
    ]:
        f.write(ar_header(aname, len(data)))
        f.write(data)
        if len(data) % 2 != 0:
            f.write(b"\n")

size = os.path.getsize(OUT)
print(f"  ✅ {OUT}")
print(f"     大小: {size} bytes ({size/1024:.1f} KB)")

# ---------- 5. 验证 ----------
print("\n🔍 验证...")

# 用 Python 解 ar 看结构
with open(OUT, "rb") as f:
    data = f.read()

assert data[:8] == b"!<arch>\n", "ar magic 错误"
print("  ✅ ar magic 正确")

pos = 8
members = []
while pos + 60 <= len(data):
    header = data[pos:pos+60]
    # 用 struct 解 ar header
    name_b, mtime_b, uid_b, gid_b, mode_b, size_b, magic = struct.unpack("16s12s6s6s8s10s2s", header)
    aname = name_b.strip().decode()
    asize = int(size_b.strip())
    pos += 60
    mdata = data[pos:pos+asize]
    members.append((aname, asize, mdata))
    pos += asize
    # ar 2-byte alignment
    if asize % 2 != 0:
        pos += 1

for name, sz, _ in members:
    print(f"  ✅ 成员: {name} ({sz} bytes)")

# 验证 gzip 完整性
import zlib
for name, sz, mdata in members:
    if name.endswith(".tar.gz"):
        try:
            zlib.decompress(mdata, 16+15)  # gzip 解压
            print(f"  ✅ {name} gzip 流完整")
        except Exception as e:
            print(f"  ❌ {name} gzip 错误: {e}")

# 列出 data.tar.gz 内容
import tarfile as tf
for name, sz, mdata in members:
    if name == "data.tar.gz":
        with gzip.GzipFile(fileobj=io.BytesIO(mdata)) as gz:
            with tf.open(fileobj=gz, mode="r:") as tar:
                print(f"\n  📁 data.tar.gz 内容:")
                for m in tar.getmembers():
                    if m.isfile():
                        print(f"    {m.name} ({m.size}B)")

print("\n🎉 构建完成!")
print(f"   安装: sudo dpkg -i {os.path.basename(OUT)}")
print(f"   验证: xpm version")

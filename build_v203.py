#!/usr/bin/env python3
"""
build_v203.py — XPM v2.0-3 终极构建（Debian-Native Edition）

流程：
1. 复制文件到构建目录
2. 在外部生成正确的 md5sums（路径相对包根）
3. 用 fakeroot 只做 chmod + dpkg-deb
   （fakeroot 让 dpkg-deb 认为权限正确）
"""

import os, sys, shutil, hashlib, subprocess

SRC = "/data/workspace/xpm"
VERSION = "2.0-3"
PKG = f"xpm_{VERSION}_all.deb"
OUT = os.path.join(SRC, PKG)

FILES = {
    "usr/local/bin/xpm":            f"{SRC}/xpm.py",
    "usr/local/bin/xm":             f"{SRC}/xm.py",
    "usr/local/bin/xm-build":       f"{SRC}/xm-build",
    "usr/local/bin/xpm-build-tool": f"{SRC}/xpm_build.py",
    "usr/local/share/xpm/docs/README.md":       f"{SRC}/README.md",
    "usr/local/share/xpm/docs/RELEASE.md":      f"{SRC}/RELEASE.md",
    "usr/local/share/xpm/docs/FAQ.md":         f"{SRC}/docs/FAQ.md",
    "usr/local/share/xpm/docs/design.md":      f"{SRC}/docs/design.md",
    "usr/local/share/xpm/docs/manual.md":      f"{SRC}/docs/manual.md",
    "usr/local/share/xpm/docs/packaging.md":   f"{SRC}/docs/packaging.md",
    "usr/local/share/xpm/docs/internals.md":   f"{SRC}/docs/internals.md",
    "usr/local/share/xpm/tests/test_all.py":   f"{SRC}/tests/test_all.py",
    "usr/share/applications/xpm.desktop": f"{SRC}/xpm.desktop",
}

def step(msg):
    print(f"\n🔧 {msg}")

def run(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"  ❌ (exit {r.returncode}): {' '.join(cmd)}")
        if r.stderr: print(f"  {r.stderr[:300]}")
        sys.exit(1)
    return r

# ─── 1. 清理 + 准备目录 ────────────────────────
step("清理旧构建")
build_root = f"{SRC}/_deb_build"
if os.path.exists(build_root):
    shutil.rmtree(build_root)

debian_dir = f"{build_root}/DEBIAN"
os.makedirs(debian_dir, exist_ok=True)

# ─── 2. 复制文件 ──────────────────────────────
step("复制文件")
for pkg_path, src_path in FILES.items():
    dst = os.path.join(build_root, pkg_path)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(src_path):
        print(f"  ⚠️  缺失: {src_path}")
        continue
    shutil.copy2(src_path, dst)
    print(f"  ✅ {pkg_path}")

# ─── 3. 写 control ────────────────────────────
step("生成 DEBIAN/control")
total_size = sum(
    os.path.getsize(os.path.join(build_root, p))
    for p in FILES if os.path.exists(os.path.join(build_root, p))
)
installed_size = total_size // 1024

control = f"""Package: xpm
Version: {VERSION}
Section: admin
Priority: optional
Architecture: all
Installed-Size: {installed_size}
Depends: python3, wget, dpkg, tar, gzip
Recommends: python3-tk, curl
Suggests: gnupg
Maintainer: Zizhao <zizhao@localhost>
Homepage: https://github.com/zizhao114514/xpm
Description: X11 Package Manager - Petroleum Edition (Debian-Native)
 XPM is a self-sovereign package manager for Debian-based systems.
 Features: dependency resolution, transaction rollback, GPG verification,
 xm-build packaging tool, GUI with progress bar, multi-language help
 (zh/en/ja), 18 practical commands. Zero apt-get usage.
 Tagline: "as if I care for your package dependencies."
 .
 Debian-Native Edition: all paths unified under /usr/local/share/xpm/,
 built with dpkg-deb for 100% apt compatibility. preinst creates all
 directories before dpkg extracts files.
"""
with open(f"{debian_dir}/control", "w") as f:
    f.write(control)
print(f"  ✅ control (Installed-Size: {installed_size}KB)")

# ─── 4. 写 preinst ────────────────────────────
step("生成 DEBIAN/preinst")
preinst = """#!/bin/sh
# XPM preinst - 在 dpkg 解包任何文件之前建好所有目录
set -e
mkdir -p /usr/local/bin
mkdir -p /usr/local/share/xpm
mkdir -p /usr/local/share/xpm/db
mkdir -p /usr/local/share/xpm/cache
mkdir -p /usr/local/share/xpm/log
mkdir -p /usr/local/share/xpm/keyring
mkdir -p /usr/local/share/xpm/transactions
mkdir -p /usr/local/share/xpm/sources.list.d
mkdir -p /usr/local/share/xpm/docs
mkdir -p /usr/local/share/xpm/tests
mkdir -p /usr/share/applications
exit 0
"""
with open(f"{debian_dir}/preinst", "w") as f:
    f.write(preinst)
print("  ✅ preinst")

# ─── 5. 写 postinst ───────────────────────────
step("生成 DEBIAN/postinst")
postinst = f"""#!/bin/sh
set -e
chmod 755 /usr/local/bin/xpm 2>/dev/null || true
chmod 755 /usr/local/bin/xm 2>/dev/null || true
chmod 755 /usr/local/bin/xm-build 2>/dev/null || true
chmod 755 /usr/local/bin/xpm-build-tool 2>/dev/null || true
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  XPM v{VERSION} installed!                ║"
echo "║  Oil reserve: 100001%                    ║"
echo "║  Apt: explicitly forbidden               ║"
echo "║  as if I care for your package deps.     ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "  Run: xpm doctor     (系统检查)"
echo "  Run: xpm help       (查看帮助)"
echo "  Run: xpm update     (更新软件源)"
echo ""
exit 0
"""
with open(f"{debian_dir}/postinst", "w") as f:
    f.write(postinst)
print("  ✅ postinst")

# ─── 6. 生成 md5sums（在 fakeroot 外部，用真实路径）──
step("生成 DEBIAN/md5sums")
md5_lines = []
for pkg_path in sorted(FILES.keys()):
    full = os.path.join(build_root, pkg_path)
    if os.path.isfile(full):
        h = hashlib.md5()
        with open(full, "rb") as f:
            h.update(f.read())
        md5_lines.append(f"{h.hexdigest()}  {pkg_path}")

md5_path = f"{debian_dir}/md5sums"
with open(md5_path, "w") as f:
    f.write("\n".join(md5_lines) + "\n")
print(f"  ✅ md5sums ({len(md5_lines)} 个文件)")

# ─── 7. 用 fakeroot + dpkg-deb 构建 ──────────
step("用 fakeroot + dpkg-deb 构建 .deb")

if os.path.exists(OUT):
    os.remove(OUT)

# fakeroot 脚本：只做 chmod + dpkg-deb
fakeroot_script = f"{SRC}/_fakeroot_build.sh"
script = f"""#!/bin/sh
# chmod DEBIAN 目录和文件
chmod 0755 {debian_dir}
chmod 0644 {debian_dir}/control
chmod 0644 {debian_dir}/md5sums
chmod 0755 {debian_dir}/preinst
chmod 0755 {debian_dir}/postinst

# chmod bin 文件
chmod 0755 {build_root}/usr/local/bin/xpm
chmod 0755 {build_root}/usr/local/bin/xm
chmod 0755 {build_root}/usr/local/bin/xm-build
chmod 0755 {build_root}/usr/local/bin/xpm-build-tool

# chmod 文档
chmod 0644 {build_root}/usr/local/share/xpm/docs/*
chmod 0644 {build_root}/usr/local/share/xpm/tests/*

# chmod desktop
chmod 0644 {build_root}/usr/share/applications/xpm.desktop

# 构建
dpkg-deb -Zgzip -b {build_root} {OUT}
"""
with open(fakeroot_script, "w") as f:
    f.write(script)
os.chmod(fakeroot_script, 0o755)

r = subprocess.run(["fakeroot", fakeroot_script], capture_output=True, text=True)
if r.returncode != 0:
    print(f"  ❌ fakeroot + dpkg-deb 失败:")
    if r.stdout: print(f"  stdout: {r.stdout[:500]}")
    if r.stderr: print(f"  stderr: {r.stderr[:500]}")
    sys.exit(1)

if not os.path.exists(OUT):
    print(f"  ❌ 输出文件不存在: {OUT}")
    sys.exit(1)

size = os.path.getsize(OUT)
print(f"  ✅ {OUT} ({size/1024:.1f} KB)")

# ─── 8. 全面验证 ──────────────────────────────
step("全面验证")

print("\n  📋 dpkg-deb -I:")
r = subprocess.run(["dpkg-deb", "-I", OUT], capture_output=True, text=True)
if r.returncode == 0:
    for line in r.stdout.strip().split("\n")[:20]:
        print(f"    {line}")
else:
    print(f"  ❌ {r.stderr}")

print("\n  📁 dpkg-deb -c (前 5 行):")
r = subprocess.run(["dpkg-deb", "-c", OUT], capture_output=True, text=True)
if r.returncode == 0:
    lines = r.stdout.strip().split("\n")
    for l in lines[:5]:
        print(f"    {l}")
    print(f"    ... 共 {len(lines)} 行")
else:
    print(f"  ❌ {r.stderr}")

print("\n  🔍 ar 结构:")
r = subprocess.run(["ar", "t", OUT], capture_output=True, text=True)
for l in r.stdout.strip().split("\n"):
    print(f"    ✅ {l}")

# gzip 完整性
import gzip, io, tarfile
print("\n  🔍 gzip + tar 内容:")
for member in ["control.tar.gz", "data.tar.gz"]:
    r = subprocess.run(["ar", "p", OUT, member], capture_output=True)
    try:
        d = gzip.decompress(r.stdout)
        # 检查 tar 内容
        with tarfile.open(fileobj=io.BytesIO(d), mode="r:") as tar:
            names = [m.name.lstrip("./") for m in tar.getmembers() if m.isfile()]
        print(f"    ✅ {member}: {len(d)}B, 含 {len(names)} 个文件 → {names}")
    except Exception as e:
        print(f"    ❌ {member}: {e}")

# ─── 9. 运行测试 ──────────────────────────────
step("运行测试套件")
r = subprocess.run([sys.executable, f"{SRC}/tests/test_all.py"],
                   capture_output=True, text=True)
for line in r.stdout.strip().split("\n"):
    if any(k in line for k in ["通过", "失败", "测试", "✅", "❌", "Summary"]):
        print(f"  {line}")

# ─── 完成 ──────────────────────────────────────
print(f"\n{'='*50}")
print(f"🎉 XPM v{VERSION} \"Debian-Native Edition\" 构建完成!")
print(f"{'='*50}")
print(f"  文件: {OUT}")
print(f"  大小: {size/1024:.1f} KB")
print(f"  安装: sudo dpkg -i {PKG}")
print(f"  验证: xpm version → xpm {VERSION}")
print(f"{'='*50}")

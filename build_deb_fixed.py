#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_deb_fixed.py — 构建 XPM .deb 包（修复版）

关键修复：
1. control.tar.gz 里必须包含 md5sums 文件（否则新版 apt 报"成员文件头无效"）
2. 使用 dpkg-deb -b 来构建（保证 ar 格式 100% 兼容）
3. 路径全部放 /usr/local/share/xpm/（proot 可写）
"""

import os
import shutil
import subprocess
import hashlib
from pathlib import Path
import tempfile

os.umask(0)

ROOT = Path(__file__).parent.resolve()
PKG = "xpm"
VER = "2.0-2"
ARCH = "all"
OUT = ROOT / f"{PKG}_{VER}_all.deb"

# 临时构建目录
TMP = Path(tempfile.mkdtemp(prefix="xpm_build_"))
PKG_DIR = TMP / PKG
DEBIAN_DIR = PKG_DIR / "DEBIAN"

def makedirs(p, mode=0o755):
    os.makedirs(p, mode=mode, exist_ok=True)
    os.chmod(p, mode)

# ---------- 创建目录结构 ----------
makedirs(PKG_DIR)
makedirs(DEBIAN_DIR)

# ---------- 复制文件 ----------
# 二进制
bin_dir = PKG_DIR / "usr/local/bin"
makedirs(bin_dir)
shutil.copy2(ROOT / "xpm.py", bin_dir / "xpm")
shutil.copy2(ROOT / "xm.py",  bin_dir / "xm")
os.chmod(bin_dir / "xpm", 0o755)
os.chmod(bin_dir / "xm",  0o755)

# 文档
doc_dir = PKG_DIR / "usr/local/share/xpm/docs"
makedirs(doc_dir)
for f in ["README.md", "RELEASE.md", "FAQ.md", "design.md",
          "internals.md", "manual.md", "packaging.md"]:
    src = ROOT / f
    if src.exists():
        shutil.copy2(src, doc_dir / f)
        os.chmod(doc_dir / f, 0o644)

# 测试
test_dir = PKG_DIR / "usr/local/share/xpm/tests"
makedirs(test_dir)
shutil.copy2(ROOT / "tests/test_all.py", test_dir / "test_all.py")
os.chmod(test_dir / "test_all.py", 0o644)

# 桌面文件
app_dir = PKG_DIR / "usr/share/applications"
makedirs(app_dir)
shutil.copy2(ROOT / "xpm.desktop", app_dir / "xpm.desktop")
os.chmod(app_dir / "xpm.desktop", 0o644)

# ---------- 生成 md5sums ----------
print("[*] 生成 md5sums ...")
md5sums_path = DEBIAN_DIR / "md5sums"
md5_lines = []
for root_dir, dirs, files in os.walk(PKG_DIR):
    for fname in sorted(files):
        fpath = os.path.join(root_dir, fname)
        rel_path = os.path.relpath(fpath, PKG_DIR)
        # md5sums 不包含 DEBIAN/ 目录下的文件
        if rel_path.startswith("DEBIAN/"):
            continue
        with open(fpath, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        md5_lines.append(f"{md5}  {rel_path}")

with open(md5sums_path, "w") as f:
    f.write("\n".join(md5_lines) + "\n")
os.chmod(md5sums_path, 0o644)

print(f"  {len(md5_lines)} 个文件已加入 md5sums")
for line in md5_lines:
    print(f"    {line[:50]}")

# ---------- 写 control 文件 ----------
control_path = DEBIAN_DIR / "control"
control_text = (
    f"Package: {PKG}\n"
    f"Version: {VER}\n"
    f"Section: admin\n"
    f"Priority: optional\n"
    f"Architecture: {ARCH}\n"
    f"Installed-Size: 160\n"
    f"Depends: python3, wget, dpkg, tar, gzip\n"
    f"Recommends: python3-tk, curl\n"
    f"Suggests: gnupg\n"
    f"Maintainer: Zizhao <zizhao@localhost>\n"
    f"Homepage: https://github.com/zizhao114514/xpm\n"
    f"Description: X11 Package Manager - Petroleum Edition\n"
    f" XPM is a self-sovereign package manager for Debian-based systems.\n"
    f" Features: dependency resolution, transaction rollback, GPG verification,\n"
    f" xm-build packaging tool, GUI with progress bar, multi-language help\n"
    f" (zh/en/ja), 18 practical commands. Zero apt-get usage.\n"
    f' Tagline: "as if I care for your package dependencies."\n'
)
control_path.write_text(control_text)
os.chmod(control_path, 0o644)

# ---------- 写 postinst ----------
postinst_path = DEBIAN_DIR / "postinst"
postinst_text = (
    "#!/bin/sh\n"
    "mkdir -p /usr/local/share/xpm/db /usr/local/share/xpm/cache /usr/local/share/xpm/log /usr/local/share/xpm/keyring\n"
    "mkdir -p /usr/local/share/xpm/docs\n"
    "mkdir -p /etc/xpm/sources.list.d\n"
    "echo \"XPM v2.0-2 installed (Fixed Edition)\"\n"
    "echo \"石油储备: 100001%\"\n"
    "echo \"as if I care for your package dependencies.\"\n"
)
postinst_path.write_text(postinst_text)
os.chmod(postinst_path, 0o755)

# ---------- 用 dpkg-deb 构建 ----------
if OUT.exists():
    OUT.unlink()

print(f"\n[*] dpkg-deb -Zgzip -b {PKG_DIR} {OUT} ...")
res = subprocess.run(
    ["dpkg-deb", "-Zgzip", "-b", str(PKG_DIR), str(OUT)],
    capture_output=True, text=True
)
if res.stdout: print(res.stdout.strip())
if res.stderr: print("STDERR:", res.stderr.strip())
if res.returncode != 0:
    raise SystemExit(f"dpkg-deb failed (rc={res.returncode})")

size = OUT.stat().st_size
print(f"[+] Built: {OUT} ({size} bytes)")

# ---------- 验证 ----------
print("\n[*] dpkg-deb -I:")
r1 = subprocess.run(["dpkg-deb", "-I", str(OUT)], capture_output=True, text=True)
print(r1.stdout)
if r1.returncode != 0:
    print("STDERR:", r1.stderr)
    raise SystemExit("dpkg-deb -I failed")

print("[*] dpkg-deb -c:")
r2 = subprocess.run(["dpkg-deb", "-c", str(OUT)], capture_output=True, text=True)
print(r2.stdout)
if r2.returncode != 0:
    print("STDERR:", r2.stderr)
    raise SystemExit("dpkg-deb -c failed")

# ---------- 验证 control.tar.gz 里有 md5sums ----------
print("[*] 验证 control.tar.gz 包含 md5sums ...")
import tarfile, io
with open(str(OUT), "rb") as f:
    # 跳过 ar magic
    f.read(8)
    # 读 debian-binary header
    h = f.read(60)
    sz = int(h[48:58].strip())
    f.read(sz + (1 if sz % 2 else 0))  # skip data + padding
    # 读 control.tar.gz header
    h = f.read(60)
    sz = int(h[48:58].strip())
    control_gz = f.read(sz)

with tarfile.open(fileobj=io.BytesIO(control_gz), mode="r:gz") as tar:
    names = tar.getnames()
    print(f"  control.tar.gz 内容: {names}")
    if "md5sums" in names:
        print("  ✅ md5sums 存在!")
    else:
        print("  ❌ md5sums 仍然缺失!")
        raise SystemExit("md5sums missing")

# ---------- 测试 ----------
print("\n[*] 运行测试 ...")
r3 = subprocess.run(["python3", str(ROOT / "tests/test_all.py")],
                    capture_output=True, text=True)
for line in r3.stdout.splitlines():
    if "通过" in line or "失败" in line or "✅" in line or "❌" in line:
        print(line)
if r3.returncode != 0 and "失败" in r3.stdout:
    print("STDERR:", r3.stderr)

print(f"\n✅ DONE — {OUT} ({size} bytes)")
print(f"   包含 md5sums，apt 不会再报错了")

# 清理
shutil.rmtree(TMP)

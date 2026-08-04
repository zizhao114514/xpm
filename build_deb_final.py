#!/usr/bin/env python3
"""
build_deb_final.py — 用 dpkg-deb 构建，强制 gzip 压缩（兼容旧 dpkg）。
关键发现：之前所有失败的根因是 dpkg-deb 默认用 zstd 压缩，
而 proot 里的旧版 dpkg 只认 gzip/bzip2/xz。
"""
import os, shutil, subprocess, stat
from pathlib import Path

os.umask(0)

ROOT = Path(__file__).parent.resolve()
PKG = "xpm"
VER = "2.0-2"
OUT = ROOT / f"{PKG}_{VER}_all.deb"

import tempfile
TMP = Path(tempfile.mkdtemp(prefix="xpm_build_"))
PKG_DIR = TMP / PKG

def makedirs(p, mode=0o755):
    os.makedirs(p, mode=mode, exist_ok=True)
    os.chmod(p, mode)

makedirs(PKG_DIR)

# ---------- 文件 ----------
bin_dir = PKG_DIR / "usr/local/bin"
makedirs(bin_dir)
shutil.copy2(ROOT / "xpm.py", bin_dir / "xpm")
shutil.copy2(ROOT / "xm.py",  bin_dir / "xm")
os.chmod(bin_dir / "xpm", 0o755)
os.chmod(bin_dir / "xm",  0o755)

doc_dir = PKG_DIR / "usr/local/share/xpm/docs"
makedirs(doc_dir)
for f in ["README.md", "RELEASE.md", "FAQ.md", "design.md",
          "internals.md", "manual.md", "packaging.md"]:
    src = ROOT / f
    if src.exists():
        shutil.copy2(src, doc_dir / f)
        os.chmod(doc_dir / f, 0o644)

test_dir = PKG_DIR / "usr/local/share/xpm/tests"
makedirs(test_dir)
shutil.copy2(ROOT / "tests/test_all.py", test_dir / "test_all.py")
os.chmod(test_dir / "test_all.py", 0o644)

app_dir = PKG_DIR / "usr/share/applications"
makedirs(app_dir)
shutil.copy2(ROOT / "xpm.desktop", app_dir / "xpm.desktop")
os.chmod(app_dir / "xpm.desktop", 0o644)

# ---------- DEBIAN/control ----------
deb_dir = PKG_DIR / "DEBIAN"
makedirs(deb_dir, 0o755)
control = deb_dir / "control"
control.write_text(
    "Package: xpm\n"
    f"Version: {VER}\n"
    "Section: admin\n"
    "Priority: optional\n"
    "Architecture: all\n"
    "Installed-Size: 160\n"
    "Depends: python3, python3-tk, wget, dpkg\n"
    "Recommends: curl\n"
    "Suggests: gnupg\n"
    "Maintainer: Zizhao <zizhao@localhost>\n"
    'Homepage: https://github.com/zizhao114514/xpm\n'
    "Description: X11 Package Manager - Petroleum Edition\n"
    " XPM is a self-sovereign package manager for Debian-based systems.\n"
    " Features: dependency resolution, transaction rollback, GPG verification,\n"
    " xm-build packaging tool, GUI with progress bar, multi-language help\n"
    " (zh/en/ja), 18 practical commands. Zero apt-get usage.\n"
    ' Tagline: "as if I care for your package dependencies."\n'
)
os.chmod(control, 0o644)

# ---------- dpkg-deb -b --compression=gzip ----------
if OUT.exists():
    OUT.unlink()

print(f"[*] Building with dpkg-deb -b (compression=gzip) ...")
res = subprocess.run(
    ["dpkg-deb", "-Zgzip", "-b", str(PKG_DIR), str(OUT)],
    capture_output=True, text=True
)
print(res.stdout)
if res.stderr:
    print("STDERR:", res.stderr)
if res.returncode != 0:
    raise SystemExit(f"dpkg-deb failed (rc={res.returncode})")

print(f"[+] Built: {OUT} ({OUT.stat().st_size} bytes)")
print(f"[*] Format: {subprocess.run(['file', str(OUT)], capture_output=True, text=True).stdout.strip()}")

# ---------- 验证 ----------
print("\n[*] dpkg-deb -I:")
r1 = subprocess.run(["dpkg-deb", "-I", str(OUT)], capture_output=True, text=True)
print(r1.stdout)
if r1.returncode != 0:
    print("STDERR:", r1.stderr); raise SystemExit("dpkg-deb -I failed")

print("[*] dpkg-deb -c:")
r2 = subprocess.run(["dpkg-deb", "-c", str(OUT)], capture_output=True, text=True)
print(r2.stdout)
if r2.returncode != 0:
    print("STDERR:", r2.stderr); raise SystemExit("dpkg-deb -c failed")

# ---------- dpkg --extract 测试 ----------
print("[*] dpkg --extract test ...")
test_ext = TMP / "ext"
makedirs(test_ext)
r_e = subprocess.run(["dpkg", "--extract", str(OUT), str(test_ext)],
                      capture_output=True, text=True)
if r_e.returncode != 0:
    print("STDERR:", r_e.stderr); raise SystemExit("extract failed")
print("  OK — files extracted:")
for p in sorted(test_ext.rglob("*")):
    if p.is_file():
        print(f"    {p.relative_to(test_ext)}")

# ---------- 测试 ----------
print("\n[*] Running tests ...")
r3 = subprocess.run(["python3", str(ROOT / "tests/test_all.py")],
                    capture_output=True, text=True)
# 只打摘要
for line in r3.stdout.splitlines():
    if "通过" in line or "失败" in line or "✅" in line or "❌" in line:
        print(line)
if r3.returncode != 0:
    print("STDERR:", r3.stderr)

print(f"\n✅ DONE — {OUT} ({OUT.stat().st_size} bytes)")
shutil.rmtree(TMP)

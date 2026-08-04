#!/usr/bin/env python3
"""
build_deb_v3.py — 用系统 dpkg-deb 构建，正确处理权限。
关键：用 os.makedirs(mode=0o755) + os.umask(0) 确保目录权限正确。
"""
import os, shutil, subprocess, stat
from pathlib import Path

# 关键：重置 umask，让 mkdir(mode=...) 真正生效
os.umask(0)

ROOT = Path(__file__).parent.resolve()
PKG = "xpm"
VER = "2.0-2"
OUT = ROOT / f"{PKG}_{VER}_all.deb"

# 用 /tmp 避免沙盒文件系统 chmod 失效
import tempfile
TMP = Path(tempfile.mkdtemp(prefix="xpm_build_"))
PKG_DIR = TMP / PKG  # dpkg-deb 打包这个目录

def makedirs(p, mode=0o755):
    os.makedirs(p, mode=mode, exist_ok=True)
    os.chmod(p, mode)

makedirs(PKG_DIR)

# ---------- 1. 文件 ----------
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

# ---------- 2. DEBIAN/control ----------
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

# 验证权限
print(f"[*] DEBIAN perms: {oct(stat.S_IMODE(os.stat(deb_dir).st_mode))}")
print(f"[*] control perms: {oct(stat.S_IMODE(os.stat(control).st_mode))}")

# ---------- 3. dpkg-deb -b ----------
print(f"[*] Building with dpkg-deb -b ...")
# 先删旧包（final 和 OUT 是同一个路径，直接写到位）
if OUT.exists():
    OUT.unlink()
# 最终输出路径 = OUT，无需再 copy
res = subprocess.run(
    ["dpkg-deb", "-b", str(PKG_DIR), str(OUT)],
    capture_output=True, text=True
)
print(res.stdout)
if res.stderr:
    print("STDERR:", res.stderr)
if res.returncode != 0:
    raise SystemExit(f"dpkg-deb -b failed (rc={res.returncode})")
print(f"[+] Built: {OUT} ({OUT.stat().st_size} bytes)")

# ---------- 4. 验证 ----------
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

# ---------- 5. 用 dpkg 安装到临时目录测试 ----------
print("[*] Testing dpkg --extract ...")
test_extract = TMP / "extract_test"
makedirs(test_extract)
r_ext = subprocess.run(
    ["dpkg", "--extract", str(OUT), str(test_extract)],
    capture_output=True, text=True
)
if r_ext.returncode != 0:
    print("STDERR:", r_ext.stderr); raise SystemExit("dpkg --extract failed")
print("  Extract OK:")
for p in sorted(test_extract.rglob("*")):
    if p.is_file():
        print(f"    {p.relative_to(test_extract)}")

# ---------- 6. 测试 ----------
print("\n[*] Running tests ...")
r3 = subprocess.run(["python3", str(ROOT / "tests/test_all.py")],
                    capture_output=True, text=True)
print(r3.stdout)
if r3.returncode != 0:
    print("STDERR:", r3.stderr); raise SystemExit("tests failed")

# ---------- 7. 完成 ----------
final = OUT
print(f"\n✅ ALL GREEN — {final} ({final.stat().st_size} bytes)")

# 清理
shutil.rmtree(TMP)

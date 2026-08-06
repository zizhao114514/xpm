#!/usr/bin/env python3
"""
XPM Debian 包构建脚本 (v2.1-0)
使用 fakeroot + dpkg-deb 一步构建
"""
import os, subprocess, shutil, sys, gzip, tarfile, hashlib, io

PKG_NAME = "xpm"
PKG_VERSION = "2.1-0"
PKG_ARCH = "all"
STAGE = "/tmp/xpm_stage"
DIST = "/data/workspace/xpm"

# 文件清单：(源路径相对DIST, 安装路径, 权限)
DATA_FILES = [
    ("xpm.py",              "usr/local/bin/xpm",              0o755),
    ("xm.py",               "usr/local/bin/xm",               0o755),
    ("xm-build.py",         "usr/local/bin/xm-build",         0o755),
    ("xpm-build-tool.py",   "usr/local/bin/xpm-build-tool",   0o755),
    ("README.md",           "usr/local/share/xpm/docs/README.md",         0o644),
    ("docs/FAQ.md",        "usr/local/share/xpm/docs/FAQ.md",          0o644),
    ("docs/design.md",     "usr/local/share/xpm/docs/design.md",       0o644),
    ("docs/manual.md",     "usr/local/share/xpm/docs/manual.md",       0o644),
    ("docs/packaging.md",  "usr/local/share/xpm/docs/packaging.md",    0o644),
    ("docs/internals.md",  "usr/local/share/xpm/docs/internals.md",   0o644),
    ("RELEASE.md",         "usr/local/share/xpm/docs/RELEASE.md",      0o644),
    ("tests/test_all.py",  "usr/local/share/xpm/tests/test_all.py",   0o755),
    ("xpm.desktop",        "usr/share/applications/xpm.desktop",      0o644),
]

def clean():
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE, exist_ok=True)

def write_text(path_rel, content, mode=0o644):
    dst = os.path.join(STAGE, path_rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w") as f:
        f.write(content)
    os.chmod(dst, mode)

def build_control():
    """生成 DEBIAN/ 目录下的控制文件"""
    ctrl = os.path.join(STAGE, "DEBIAN")
    os.makedirs(ctrl, exist_ok=True)
    os.chmod(ctrl, 0o755)

    control = f"""Package: xpm
Version: {PKG_VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), ca-certificates
Recommends: wget, curl
Maintainer: Zizhao <zizhao114514@users.noreply.github.com>
Description: XPM - 石油派系终极包管理器
 XPM (Xinghua Package Manager) 是一个独立的包管理系统，
 使用石油储备百分比作为进度条，功耗模拟作为状态指示。
 支持 install / remove / update / search / self-update 等命令。
 完全独立于 apt/dpkg 数据库，不污染系统包管理。
"""
    write_text("DEBIAN/control", control, 0o644)

    preinst = """#!/bin/bash
set -e
mkdir -p /usr/local/bin
mkdir -p /usr/local/share/xpm/docs
mkdir -p /usr/local/share/xpm/tests
mkdir -p /usr/local/share/xpm/sources.list.d
mkdir -p /usr/local/share/xpm/cache
mkdir -p /usr/local/share/xpm/installed
mkdir -p /usr/local/share/xpm/state
mkdir -p /usr/share/applications
echo "[i] XPM: 准备安装目录..."
exit 0
"""
    write_text("DEBIAN/preinst", preinst, 0o755)

    postinst = f"""#!/bin/bash
set -e
chmod 755 /usr/local/bin/xpm 2>/dev/null || true
chmod 755 /usr/local/bin/xm 2>/dev/null || true
chmod 755 /usr/local/bin/xm-build 2>/dev/null || true
chmod 755 /usr/local/bin/xpm-build-tool 2>/dev/null || true
if [ ! -f /usr/local/share/xpm/sources.list.d/tuna.list ]; then
    cat > /usr/local/share/xpm/sources.list.d/tuna.list << 'EOF'
deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main contrib non-free non-free-firmware
EOF
fi
echo "[✓] XPM v{PKG_VERSION} 安装完成"
echo "    石油储备 100001% | 功耗 1.x W"
exit 0
"""
    write_text("DEBIAN/postinst", postinst, 0o755)

def build_data():
    """把数据文件复制到 staging 目录，保持目标路径"""
    for src_rel, dst_rel, mode in DATA_FILES:
        src = os.path.join(DIST, src_rel)
        if not os.path.exists(src):
            print(f"  [!] 跳过缺失: {src_rel}")
            continue
        dst = os.path.join(STAGE, dst_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        os.chmod(dst, mode)

def build_md5sums():
    """生成 md5sums"""
    ctrl = os.path.join(STAGE, "DEBIAN")
    os.chmod(ctrl, 0o755)
    md5sums = ""
    for root, dirs, files in os.walk(STAGE):
        for f in sorted(files):
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, STAGE)
            if rel.startswith("DEBIAN/"):
                continue
            h = hashlib.md5(open(fp, "rb").read()).hexdigest()
            md5sums += f"{h}  {rel}\n"
    write_text("DEBIAN/md5sums", md5sums, 0o644)

def build_deb():
    clean()

    # 1. 控制文件
    build_control()

    # 2. 数据文件
    build_data()

    # 3. md5sums
    build_md5sums()

    # 4. 修复权限（fakeroot 下 chmod 可能不生效）
    ctrl_dir = os.path.join(STAGE, "DEBIAN")
    os.chmod(ctrl_dir, 0o755)
    for root, dirs, files in os.walk(STAGE):
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o755)
        for f in files:
            fp = os.path.join(root, f)
            if fp.endswith(("preinst", "postinst")):
                os.chmod(fp, 0o755)
            else:
                os.chmod(fp, 0o644)

    # 4. 用 fakeroot + dpkg-deb 构建
    output = os.path.join(DIST, f"{PKG_NAME}_{PKG_VERSION}_{PKG_ARCH}.deb")
    if os.path.exists(output):
        os.remove(output)

    cmd = f"fakeroot dpkg-deb -Zgzip -b {STAGE} {output}"
    print(f"[i] {cmd}")
    ret = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if ret.returncode != 0:
        print(f"[✗] dpkg-deb 失败:")
        print(ret.stdout)
        print(ret.stderr)
        sys.exit(1)

    size = os.path.getsize(output)
    print(f"[✓] 构建完成: {output} ({size} bytes)")

    verify_deb(output)

def verify_deb(path):
    print("\n[i] 验证 .deb ...")

    with open(path, "rb") as f:
        magic = f.read(8)
    assert magic == b"!<arch>\n", f"ar magic 错误: {magic!r}"
    print("  [✓] ar magic 正确")

    r = subprocess.run(["dpkg-deb", "-I", path], capture_output=True, text=True)
    assert r.returncode == 0, f"dpkg-deb -I: {r.stderr}"
    print("  [✓] dpkg-deb -I 通过")

    r = subprocess.run(["dpkg-deb", "-c", path], capture_output=True, text=True)
    assert r.returncode == 0, f"dpkg-deb -c: {r.stderr}"
    lines = r.stdout.strip().split("\n")
    print(f"  [✓] dpkg-deb -c 通过 ({len(lines)} 个文件)")

    # 验证是 gz 压缩
    r = subprocess.run(["ar", "t", path], capture_output=True, text=True)
    for m in r.stdout.strip().split("\n"):
        if m.endswith(".tar.gz"):
            extract_dir = "/tmp/xpm_verify_" + str(os.getpid())
            os.makedirs(extract_dir, exist_ok=True)
            subprocess.run(["ar", "x", path, m, "--output", extract_dir], check=True)
            gz_path = os.path.join(extract_dir, m)
            with open(gz_path, "rb") as f:
                header = f.read(2)
            assert header == b"\x1f\x8b", f"gzip magic 错误: {header!r}"
            print(f"  [✓] {m} gzip 头正确")
            shutil.rmtree(extract_dir, ignore_errors=True)

    print("\n[✓] 全部验证通过！")

if __name__ == "__main__":
    build_deb()

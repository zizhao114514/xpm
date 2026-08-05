#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_deb.py - 构建 XPM .deb 包
v2.0-5 - Mirror-Fixed Edition
"""

import os
import subprocess
import shutil

VERSION = "2.0-5"
ARCH = "all"
BASE = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = "/tmp/xpm_deb_build"

# 文件清单 (源路径相对 BASE -> deb 内路径 -> 权限)
FILES = [
    ("xpm.py",              "usr/local/bin/xpm",              0o755),
    ("xm.py",               "usr/local/bin/xm",               0o755),
    ("xpm_build.py",        "usr/local/bin/xpm_build",        0o755),
    ("README.md",           "usr/local/share/xpm/docs/README.md",         0o644),
    ("RELEASE.md",          "usr/local/share/xpm/docs/RELEASE.md",        0o644),
    ("docs/design.md",      "usr/local/share/xpm/docs/design.md",         0o644),
    ("docs/manual.md",      "usr/local/share/xpm/docs/manual.md",         0o644),
    ("docs/packaging.md",   "usr/local/share/xpm/docs/packaging.md",      0o644),
    ("docs/FAQ.md",         "usr/local/share/xpm/docs/FAQ.md",            0o644),
    ("docs/internals.md",   "usr/local/share/xpm/docs/internals.md",      0o644),
    ("tests/test_all.py",   "usr/local/share/xpm/docs/tests/test_all.py", 0o644),
    ("xpm.desktop",         "usr/share/applications/xpm.desktop", 0o644),
]

CONTROL_TEXT = f"""Package: xpm
Version: {VERSION}
Section: admin
Priority: optional
Architecture: {ARCH}
Depends: python3, wget, dpkg, tar, gzip
Recommends: python3-tk, libgdk-pixbuf2.0-0
Maintainer: zizhao <zizhao@localhost>
Homepage: https://github.com/zizhao114514/xpm
Description: XPM - X11 Package Manager (石油驱动版)
 零 apt 调用，纯 wget + dpkg 的包管理器。
 支持依赖解析、事务回滚、GPG 校验、GUI 进度条。
 中文优先帮助系统，4 阶段安装输出。
 18 个实用命令全覆盖。
 石油储备 100001%，功耗 1.x W。
"""

POSTINST_TEXT = """#!/bin/sh
mkdir -p /usr/local/share/xpm/db /usr/local/share/xpm/cache /usr/local/share/xpm/log /usr/local/share/xpm/keyring
mkdir -p /usr/local/share/xpm/docs
mkdir -p /usr/local/share/xpm/docs/tests
mkdir -p /etc/xpm/sources.list.d
echo "XPM v2.0-5 installed (Mirror-Fixed Edition)"
echo "石油储备: 100001%"
echo "as if I care for your package dependencies."
"""


def run(cmd, cwd=None):
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ❌ 失败: {r.stderr.strip()}")
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return r.stdout.strip()


def build_deb():
    # 清理
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    debian_dir = os.path.join(BUILD_DIR, "DEBIAN")
    os.makedirs(debian_dir, exist_ok=True)

    # 复制文件
    print("📦 复制文件...")
    for src_rel, arcname, mode in FILES:
        src_path = os.path.join(BASE, src_rel)
        if not os.path.exists(src_path):
            print(f"  ⚠️ 跳过不存在: {src_rel}")
            continue
        dest = os.path.join(BUILD_DIR, arcname)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src_path, dest)
        os.chmod(dest, mode)
        print(f"  + {arcname}")

    # 写 control
    ctrl_path = os.path.join(debian_dir, "control")
    with open(ctrl_path, "w") as f:
        f.write(CONTROL_TEXT)
    print(f"  + DEBIAN/control")

    # 写 postinst
    postinst_path = os.path.join(debian_dir, "postinst")
    with open(postinst_path, "w") as f:
        f.write(POSTINST_TEXT)
    os.chmod(postinst_path, 0o755)
    print(f"  + DEBIAN/postinst")

    # 生成 md5sums
    print("📦 生成 md5sums...")
    md5_path = os.path.join(debian_dir, "md5sums")
    with open(md5_path, "w") as f:
        for root, dirs, files in os.walk(BUILD_DIR):
            # 跳过 DEBIAN 目录
            dirs[:] = [d for d in dirs if d != "DEBIAN"]
            for fn in sorted(files):
                fp = os.path.join(root, fn)
                rel = os.path.relpath(fp, BUILD_DIR)
                import hashlib
                h = hashlib.md5(open(fp, "rb").read()).hexdigest()
                f.write(f"{h}  {rel}\n")
    print(f"  + DEBIAN/md5sums")

    # fakeroot + dpkg-deb -Zgzip -b
    deb_name = f"xpm_{VERSION}_all.deb"
    deb_path = os.path.join(BASE, deb_name)
    if os.path.exists(deb_path):
        os.unlink(deb_path)

    print(f"📦 构建 {deb_name} (fakeroot + dpkg-deb -Zgzip)...")
    run(["fakeroot", "dpkg-deb", "-Zgzip", "-b", BUILD_DIR, deb_path])

    size = os.path.getsize(deb_path)
    print(f"\n✅ 构建完成: {deb_name}")
    print(f"   大小: {size} bytes ({size // 1024} KB)")

    # 验证
    print(f"\n🔍 验证...")
    r = subprocess.run(["dpkg-deb", "-I", deb_path], capture_output=True, text=True)
    if r.returncode == 0:
        print("  ✅ dpkg-deb -I 通过")
    else:
        print(f"  ❌ dpkg-deb -I 失败: {r.stderr}")
        return None

    r = subprocess.run(["dpkg-deb", "-c", deb_path], capture_output=True, text=True)
    if r.returncode == 0:
        file_count = len(r.stdout.strip().split("\n"))
        print(f"  ✅ dpkg-deb -c 通过 ({file_count} 个文件)")
    else:
        print(f"  ❌ dpkg-deb -c 失败: {r.stderr}")
        return None

    return deb_path


if __name__ == "__main__":
    deb = build_deb()
    if deb:
        print(f"\n🛢️ {os.path.basename(deb)} 已就绪")
        print(f"   石油储备: 100001%")
        print(f"   功耗: 1.x W")
        print(f"   as if I care for your package dependencies.")

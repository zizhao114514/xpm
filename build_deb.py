#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_deb.py - 构建 XPM .deb 包
v2.0-7 - Ar-Standard Edition
使用 dpkg-deb 构建后，用标准 ar 命令重新打包，
确保 ar header magic 兼容性最大化。
"""

import os
import subprocess
import shutil
import hashlib
import json

VERSION = "2.0-7"
ARCH = "all"
BASE = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = "/tmp/xpm_deb_build_v207"

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
 支持 self-update 自动检查更新。
 石油储备 100001%，功耗 1.x W。
"""

POSTINST_TEXT = f"""#!/bin/sh
mkdir -p /usr/local/share/xpm/db /usr/local/share/xpm/cache /usr/local/share/xpm/log /usr/local/share/xpm/keyring
mkdir -p /usr/local/share/xpm/docs
mkdir -p /usr/local/share/xpm/docs/tests
mkdir -p /usr/local/share/xpm/sources.list.d
echo "XPM v{VERSION} installed (Ar-Standard Edition)"
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

    # 复制文件到构建目录
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
    md5_entries = []
    for root, dirs, files in os.walk(BUILD_DIR):
        dirs[:] = [d for d in dirs if d != "DEBIAN"]
        for fn in sorted(files):
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, BUILD_DIR)
            h = hashlib.md5(open(fp, "rb").read()).hexdigest()
            md5_entries.append(f"{h}  {rel}")
    with open(md5_path, "w") as f:
        f.write("\n".join(md5_entries) + "\n")
    print(f"  + DEBIAN/md5sums ({len(md5_entries)} 条)")

    # 第一步：用 dpkg-deb 构建标准 .deb（确保 tar.gz 内容正确）
    deb_raw = os.path.join(BUILD_DIR, f"xpm_{VERSION}_raw.deb")
    print(f"\n📦 [1/2] dpkg-deb 构建 (fakeroot + gzip)...")
    run(["fakeroot", "dpkg-deb", "-Zgzip", "-b", BUILD_DIR, deb_raw])

    # 解包 dpkg-deb 的结果，取出三个文件
    extract_dir = os.path.join(BUILD_DIR, "ar_extract")
    os.makedirs(extract_dir, exist_ok=True)
    run(["ar", "x", deb_raw, "--output", extract_dir])

    print(f"\n  解包内容:")
    for f in sorted(os.listdir(extract_dir)):
        fp = os.path.join(extract_dir, f)
        print(f"    {f} ({os.path.getsize(fp)} bytes)")

    # 验证三个文件都在
    required = ["debian-binary", "control.tar.gz", "data.tar.gz"]
    for r in required:
        if not os.path.exists(os.path.join(extract_dir, r)):
            raise RuntimeError(f"缺少 ar 成员: {r}")

    # 验证 debian-binary 内容
    with open(os.path.join(extract_dir, "debian-binary"), "rb") as f:
        db_content = f.read()
    print(f"\n  debian-binary 内容: {db_content!r}")
    if db_content not in (b"2.0\n", b"2.0"):
        print(f"  ⚠️ debian-binary 内容异常，修复为 2.0\\n")
        with open(os.path.join(extract_dir, "debian-binary"), "wb") as f:
            f.write(b"2.0\n")

    # 验证 gzip 完整性
    for gz_name in ["control.tar.gz", "data.tar.gz"]:
        gz_path = os.path.join(extract_dir, gz_name)
        import gzip as gz_module
        try:
            with gz_module.open(gz_path, "rb") as g:
                data = g.read()
            print(f"  ✅ {gz_name}: gzip OK ({len(data)} bytes decompressed)")
        except Exception as e:
            raise RuntimeError(f"{gz_name} gzip 损坏: {e}")

    # 第二步：用标准 `ar` 命令重新打包（magic = '  ' 空格空格，最大兼容）
    deb_final = os.path.join(BASE, f"xpm_{VERSION}_all.deb")
    if os.path.exists(deb_final):
        os.unlink(deb_final)

    print(f"\n📦 [2/2] 用标准 ar 命令重新打包（兼容性最大化）...")

    # ar 命令要求输入文件存在，且顺序为：debian-binary, control.tar.gz, data.tar.gz
    # 使用 `ar rcs` 创建归档
    cmd = [
        "ar", "rcs", deb_final,
        os.path.join(extract_dir, "debian-binary"),
        os.path.join(extract_dir, "control.tar.gz"),
        os.path.join(extract_dir, "data.tar.gz"),
    ]
    run(cmd)

    size = os.path.getsize(deb_final)
    print(f"\n✅ 构建完成: xpm_{VERSION}_all.deb")
    print(f"   大小: {size} bytes ({size // 1024} KB)")

    # 验证 ar 结构
    print(f"\n🔍 验证 ar 结构...")
    verify_ar_structure(deb_final)

    # 验证 dpkg-deb 能读
    print(f"\n🔍 dpkg-deb 验证...")
    r = subprocess.run(["dpkg-deb", "-I", deb_final], capture_output=True, text=True)
    if r.returncode == 0:
        print("  ✅ dpkg-deb -I 通过")
    else:
        print(f"  ❌ dpkg-deb -I 失败: {r.stderr}")
        return None

    r = subprocess.run(["dpkg-deb", "-c", deb_final], capture_output=True, text=True)
    if r.returncode == 0:
        file_count = len(r.stdout.strip().split("\n"))
        print(f"  ✅ dpkg-deb -c 通过 ({file_count} 个文件)")
    else:
        print(f"  ❌ dpkg-deb -c 失败: {r.stderr}")
        return None

    # 验证 ar 成员可以被 ar 命令正确读取
    print(f"\n🔍 ar 命令验证...")
    r = subprocess.run(["ar", "t", deb_final], capture_output=True, text=True)
    if r.returncode == 0:
        members = r.stdout.strip().split("\n")
        print(f"  ✅ ar 成员: {members}")
    else:
        print(f"  ❌ ar 失败: {r.stderr}")

    return deb_final


def verify_ar_structure(deb_path):
    """详细验证 ar 归档结构"""
    with open(deb_path, "rb") as f:
        data = f.read()

    # 检查全局 magic
    if data[:8] != b"!<arch>\n":
        print(f"  ❌ 全局 magic 错误: {data[:8]!r}")
        return False
    print(f"  ✅ 全局 magic: !<arch>\\n")

    pos = 8
    members = []
    while pos + 60 <= len(data):
        header = data[pos:pos+60]
        name = header[0:16].rstrip(b" ").rstrip(b"/").decode("ascii", errors="replace")
        mtime = header[16:28].strip(b" ").decode("ascii", errors="replace")
        uid = header[28:34].strip(b" ").decode("ascii", errors="replace")
        gid = header[34:40].strip(b" ").decode("ascii", errors="replace")
        mode = header[40:48].strip(b" ").decode("ascii", errors="replace")
        size_str = header[48:58].strip(b" ")
        magic = header[58:60]

        try:
            size = int(size_str) if size_str else 0
        except ValueError:
            print(f"  ❌ 成员 {name}: size 字段无效 {size_str!r}")
            size = 0

        print(f"  📄 {name}: size={size}, magic={magic!r}, mode={mode}")

        members.append(name)
        pos += 60 + size
        # ar 2-byte alignment
        if size % 2 == 1:
            pos += 1

    # 验证三个必需成员
    required = {"debian-binary", "control.tar.gz", "data.tar.gz"}
    found = set(members)
    missing = required - found
    if missing:
        print(f"  ❌ 缺少成员: {missing}")
        return False

    print(f"  ✅ 所有必需成员存在")
    return True


if __name__ == "__main__":
    deb = build_deb()
    if deb:
        print(f"\n🛢️ {os.path.basename(deb)} 已就绪")
        print(f"   石油储备: 100001%")
        print(f"   功耗: 1.x W")
        print(f"   as if I care for your package dependencies.")

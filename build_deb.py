#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_deb.py - 纯 Python 构建 XPM .deb 包
v2.0-1 - 标准 ar 格式（dpkg-deb 兼容）
"""

import os
import time
import io
import tarfile

VERSION = "2.0-2"
ARCH = "all"
BASE = os.path.dirname(os.path.abspath(__file__))

# 文件清单 (源路径相对 BASE -> deb 内路径 -> 权限)
# 所有数据文件放 /usr/local/share/xpm/（proot 一定可写）
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

CONTROL_TEXT = (
    f"Package: xpm\n"
    f"Version: {VERSION}\n"
    f"Section: admin\n"
    f"Priority: optional\n"
    f"Architecture: {ARCH}\n"
    f"Depends: python3, wget, dpkg, tar, gzip\n"
    f"Recommends: python3-tk, libgdk-pixbuf2.0-0\n"
    f"Maintainer: zizhao <zizhao@localhost>\n"
    f"Homepage: https://github.com/zizhao114514/xpm\n"
    f"Description: XPM - X11 Package Manager (石油驱动版)\n"
    f" 零 apt 调用，纯 wget + dpkg 的包管理器。\n"
    f" 支持依赖解析、事务回滚、GPG 校验、GUI 进度条。\n"
    f" 中文优先帮助系统，4 阶段安装输出。\n"
    f" 18 个实用命令全覆盖。\n"
    f" 石油储备 100001%，功耗 1.x W。\n"
)

POSTINST_TEXT = (
    "#!/bin/sh\n"
    "mkdir -p /usr/local/share/xpm/db /usr/local/share/xpm/cache /usr/local/share/xpm/log /usr/local/share/xpm/keyring\n"
    "mkdir -p /usr/local/share/xpm/docs\n"
    "mkdir -p /etc/xpm/sources.list.d\n"
    "echo \"XPM v2.0-2 installed (Proot-Friendly Edition)\"\n"
    "echo \"石油储备: 100001%\"\n"
    "echo \"as if I care for your package dependencies.\"\n"
)


def make_tar_gz(members, dest_path):
    """members: list of (arcname, source_path_or_bytes, mode)"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for arcname, payload, mode in members:
            if isinstance(payload, bytes):
                ti = tarfile.TarInfo(name=arcname)
                ti.size = len(payload)
                ti.mode = mode
                ti.mtime = int(time.time())
                ti.uid = 0
                ti.gid = 0
                tar.addfile(ti, io.BytesIO(payload))
            else:
                if not os.path.exists(payload):
                    print(f"  ⚠️ 跳过不存在的文件: {payload}")
                    continue
                st = os.stat(payload)
                ti = tarfile.TarInfo(name=arcname)
                ti.size = st.st_size
                ti.mode = mode
                ti.mtime = int(st.st_mtime)
                ti.uid = 0
                ti.gid = 0
                with open(payload, "rb") as f:
                    tar.addfile(ti, f)
    buf.seek(0)
    with open(dest_path, "wb") as f:
        f.write(buf.read())
    print(f"  ✅ {dest_path} ({os.path.getsize(dest_path)} bytes)")


def write_ar_header(out, name, size):
    """
    标准 ar header (60 字节), dpkg-deb 兼容:
    name(16 左对齐) + mtime(12 右对齐) + uid(6 右对齐) + gid(6 右对齐) + mode(8 右对齐) + size(10 右对齐) + magic(2 = 0x60+0x0A)
    """
    # name: 左对齐，空格填充到 16
    name_b = name.encode("ascii")[:16]
    name_field = name_b + b" " * (16 - len(name_b))

    # 数字字段: 右对齐，空格在左边
    def right_align(val_str, width):
        s = val_str[:width]
        return b" " * (width - len(s)) + s.encode("ascii")

    mtime_field = right_align(str(int(time.time())), 12)
    uid_field = right_align("0", 6)
    gid_field = right_align("0", 6)
    mode_field = right_align("100644", 8)
    size_field = right_align(str(size), 10)

    # magic: 0x60 + 0x0A = "`\n"
    magic = b"\x60\x0a"

    header = name_field + mtime_field + uid_field + gid_field + mode_field + size_field + magic
    assert len(header) == 60, f"AR header size wrong: {len(header)} (expected 60)"
    out.write(header)


def write_ar_member(out, name, data):
    """写入完整 ar 成员"""
    write_ar_header(out, name, len(data))
    out.write(data)
    # 2 字节对齐
    if len(data) % 2 != 0:
        out.write(b"\n")


def build_deb():
    os.chdir(BASE)

    # 清理
    for f in ["debian-binary", "control.tar.gz", "data.tar.gz",
              f"xpm_{VERSION}_all.deb"]:
        if os.path.exists(f):
            os.unlink(f)

    # ---- data.tar.gz ----
    print("📦 构建 data.tar.gz ...")
    data_members = []
    for src_rel, arcname, mode in FILES:
        src_path = os.path.join(BASE, src_rel)
        if os.path.exists(src_path):
            data_members.append((arcname, src_path, mode))
            print(f"  + {arcname}")
        else:
            print(f"  ⚠️ 源文件不存在: {src_rel}")
    make_tar_gz(data_members, "data.tar.gz")

    # ---- control.tar.gz ----
    print("📦 构建 control.tar.gz ...")
    control_members = [
        ("control", CONTROL_TEXT.encode("utf-8"), 0o644),
        ("postinst", POSTINST_TEXT.encode("utf-8"), 0o755),
    ]
    make_tar_gz(control_members, "control.tar.gz")

    # ---- debian-binary ----
    with open("debian-binary", "wb") as f:
        f.write(b"2.0\n")
    print("  ✅ debian-binary")

    # ---- 读取数据 ----
    with open("debian-binary", "rb") as f:
        debian_binary = f.read()
    with open("control.tar.gz", "rb") as f:
        control_data = f.read()
    with open("data.tar.gz", "rb") as f:
        data_data = f.read()

    print(f"  debian-binary: {len(debian_binary)} bytes")
    print(f"  control.tar.gz: {len(control_data)} bytes")
    print(f"  data.tar.gz: {len(data_data)} bytes")

    # ---- 打包 .deb ----
    deb_name = f"xpm_{VERSION}_all.deb"
    print(f"📦 打包 {deb_name} ...")

    with open(deb_name, "wb") as out:
        out.write(b"!<arch>\n")
        write_ar_member(out, "debian-binary", debian_binary)
        write_ar_member(out, "control.tar.gz", control_data)
        write_ar_member(out, "data.tar.gz", data_data)

    # ---- 验证 ----
    print(f"\n🔍 验证 ar 结构...")
    with open(deb_name, "rb") as f:
        raw = f.read()

    pos = 8  # skip !<arch>\n
    member_count = 0
    while pos + 60 <= len(raw):
        header = raw[pos:pos+60]
        name = header[0:16].rstrip(b" ").decode("ascii", errors="replace")
        size_str = header[48:58].strip().decode("ascii", errors="replace")
        magic = header[58:60]
        try:
            size = int(size_str)
        except ValueError:
            print(f"  ❌ 无法解析 size at pos {pos}: {size_str!r}")
            break
        print(f"  ✅ [{member_count}] {name:20s} size={size:>8d}  magic={magic.hex()}")
        member_count += 1
        pos += 60 + size
        if size % 2 != 0:
            pos += 1

    assert member_count == 3, f"应该有 3 个 ar 成员，实际 {member_count}"

    # ---- 清理 ----
    for f in ["debian-binary", "control.tar.gz", "data.tar.gz"]:
        if os.path.exists(f):
            os.unlink(f)

    size = os.path.getsize(deb_name)
    print(f"\n✅ 构建完成: {deb_name}")
    print(f"   大小: {size} bytes ({size // 1024} KB)")
    return deb_name


if __name__ == "__main__":
    deb = build_deb()
    print(f"\n🛢️ {deb} 已就绪")
    print(f"   石油储备: 100001%")
    print(f"   功耗: 1.x W")
    print(f"   as if I care for your package dependencies.")

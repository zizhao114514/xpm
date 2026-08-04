#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_deb.py - 构建 xpm .deb 包（纯 Python，不依赖 dpkg-deb）
用法: python3 build_deb.py [version]
"""

import os, sys, struct, hashlib, time, io, gzip
from pathlib import Path

VERSION = sys.argv[1] if len(sys.argv) > 1 else "2.0-0"
PKG_NAME = "xpm"
ARCH = "all"

# ====== ar 归档 ======
def write_ar_archive(out_path, members):
    """members: list of (name, content_bytes)"""
    with open(out_path, "wb") as f:
        f.write(b"!<arch>\n")
        for name, content in members:
            # ar 成员头: 16+12+6+6+8+10+2 = 60 bytes
            name_b = name.encode()[:16].ljust(16, b" ")
            # 时间戳
            mtime = str(int(time.time()))
            header = (
                name_b +
                b"0           " +  # mtime placeholder
                b"0     " +          # uid
                b"0     " +          # gid
                b"100644  " +        # mode
                f"{len(content):8d}".encode().rjust(10, b" ") +
                b"\x60\x0a"
            )
            f.write(header)
            f.write(content)
            # 2-byte 对齐
            if len(content) % 2 != 0:
                f.write(b"\n")

# ====== 构建 control.tar.gz ======
def build_control_tar_gz():
    """构建 control.tar.gz 的内容（用 tarfile 模块）"""
    import tarfile
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # control 文件
        control_content = f"""Package: {PKG_NAME}
Version: {VERSION}
Section: admin
Priority: optional
Architecture: {ARCH}
Depends: python3, python3-tk, wget, dpkg, tar, gzip
Suggests: mono-runtime | dotnet-runtime-8.0
Maintainer: Zizhao <zizhao@example.com>
Description: X11 Package Manager - Oil-driven, apt-forbidden
 XPM is a package manager that does not use apt.
 It uses wget for downloads and dpkg for installation.
 Backend is language-agnostic (Python/C#).
 Oil reserve: 100001%.
""".encode()

        info = tarfile.TarInfo(name="control")
        info.size = len(control_content)
        info.mtime = int(time.time())
        tar.addfile(info, io.BytesIO(control_content))

        # postinst
        postinst = (
            b"#!/bin/sh\nset -e\n"
            b"# Build C# backend if mono/dotnet available\n"
            b"if [ -d /opt/xpm-csharp ] && [ -f /opt/xpm-csharp/build.sh ]; then\n"
            b"    if command -v mcs >/dev/null 2>&1; then\n"
            b"        cd /opt/xpm-csharp && sh build.sh 2>/dev/null || true\n"
            b"    fi\n"
            b"fi\n"
            b"mkdir -p /var/lib/xpm /var/cache/xpm /var/log/xpm /etc/xpm/sources.list.d\n"
            b"mkdir -p /opt/xpm/docs /opt/xpm/tests\n"
            b"[ -f /var/lib/xpm/status.db ] || echo '{}' > /var/lib/xpm/status.db\n"
            b"[ -f /var/lib/xpm/coffee.json ] || echo '{\"crashes\":0}' > /var/lib/xpm/coffee.json\n"
            b"echo \"XPM v" + VERSION.encode() + b" installed.\"\n"
            b"echo \"Oil reserve: 100001%\"\n"
            b"echo \"Apt: explicitly forbidden\"\n"
            b"exit 0\n"
        )

        info2 = tarfile.TarInfo(name="postinst")
        info2.size = len(postinst)
        info2.mtime = int(time.time())
        info2.mode = 0o755
        tar.addfile(info2, io.BytesIO(postinst))

        # prerm
        prerm = b"""#!/bin/sh
set -e
echo "XPM: refusing to remove. as if I care."
exit 0
"""
        info3 = tarfile.TarInfo(name="prerm")
        info3.size = len(prerm)
        info3.mtime = int(time.time())
        info3.mode = 0o755
        tar.addfile(info3, io.BytesIO(prerm))

    return buf.getvalue()

# ====== 构建 data.tar.gz ======
def build_data_tar_gz():
    """构建 data.tar.gz（实际安装的文件）"""
    import tarfile
    buf = io.BytesIO()

    # 收集文件
    files_to_pack = []

    # xpm.py → /usr/local/bin/xpm
    xpm_py = Path("xpm.py")
    if xpm_py.exists():
        files_to_pack.append(("xpm.py", xpm_py.read_bytes(), "/usr/local/bin/xpm", 0o755))

    # xm.py → /usr/local/bin/xm
    xm_py = Path("xm.py")
    if xm_py.exists():
        files_to_pack.append(("xm.py", xm_py.read_bytes(), "/usr/local/bin/xm", 0o755))

    # xpm-csharp/ → /opt/xpm-csharp/
    csharp_dir = Path("xpm-csharp")
    if csharp_dir.is_dir():
        for f in csharp_dir.rglob("*"):
            if f.is_file():
                rel = f.relative_to(csharp_dir)
                target = f"/opt/xpm-csharp/{rel}"
                files_to_pack.append((str(f), f.read_bytes(), target, 0o644))

    # docs/ → /opt/xpm/docs/  (avoid /usr/share/doc permission issues in proot)
    docs_dir = Path("docs")
    if docs_dir.is_dir():
        for f in docs_dir.rglob("*"):
            if f.is_file():
                rel = f.relative_to(docs_dir)
                target = f"/opt/xpm/docs/{rel}"
                files_to_pack.append((str(f), f.read_bytes(), target, 0o644))

    # tests/ → /opt/xpm/tests/  (avoid /usr/share/doc permission issues in proot)
    tests_dir = Path("tests")
    if tests_dir.is_dir():
        for f in tests_dir.rglob("*"):
            if f.is_file():
                rel = f.relative_to(tests_dir)
                target = f"/opt/xpm/tests/{rel}"
                files_to_pack.append((str(f), f.read_bytes(), target, 0o644))

    # xpm.desktop → /usr/share/applications/
    desktop = Path("xpm.desktop")
    if desktop.exists():
        files_to_pack.append(("xpm.desktop", desktop.read_bytes(), "/usr/share/applications/xpm.desktop", 0o644))

    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for src_name, content, target, mode in files_to_pack:
            info = tarfile.TarInfo(name=target.lstrip("/"))
            info.size = len(content)
            info.mtime = int(time.time())
            info.mode = mode
            tar.addfile(info, io.BytesIO(content))

    return buf.getvalue()

# ====== 构建 debian-binary ======
DEBIAN_BINARY = b"2.0\n"

# ====== 主流程 ======
def main():
    print(f"🔧 构建 XPM v{VERSION} .deb 包...")

    # 构建各部分
    control_tar_gz = build_control_tar_gz()
    data_tar_gz = build_data_tar_gz()

    # 写 ar 归档
    out_name = f"{PKG_NAME}_{VERSION}_{ARCH}.deb"
    write_ar_archive(out_name, [
        ("debian-binary", DEBIAN_BINARY),
        ("control.tar.gz", control_tar_gz),
        ("data.tar.gz", data_tar_gz),
    ])

    size = os.path.getsize(out_name)
    print(f"✅ 构建完成: {out_name} ({size} bytes)")

    # 验证
    import subprocess
    rc = subprocess.run(["ar", "t", out_name], capture_output=True, text=True)
    if rc.returncode == 0:
        print(f"  ar 内容: {rc.stdout.strip()}")
    else:
        print(f"  ⚠️ ar 验证跳过（ar 未安装）")

    return 0

if __name__ == "__main__":
    sys.exit(main())

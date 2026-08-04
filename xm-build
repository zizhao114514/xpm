#!/usr/bin/env python3
"""
xm-build - XPM 包构建工具
将"程序安装目录及文件/"打包成 .oil 包

用法:
    xm-build <目录> [--output <path>] [--sign <key>]

目录结构要求:
    程序安装目录及文件/
    ├── usr/bin/myprog
    ├── usr/share/man/man1/myprog.1
    ├── etc/myprog.conf
    └── xpm/
        ├── control          (必须: Package, Version, Architecture)
        ├── files.list       (自动生成)
        ├── checksums.sha256 (自动生成)
        └── pmadd/           (可选脚本)
            ├── preinst
            ├── postinst
            ├── prerm
            └── postrm
"""

import os
import sys
import hashlib
import tarfile
import gzip
import argparse
import subprocess
from datetime import datetime

REQUIRED_FIELDS = ["Package", "Version", "Architecture"]

def read_control(control_path):
    """读取 xpm/control 文件，返回 dict"""
    fields = {}
    current_key = None
    with open(control_path) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith(" "):
                # 续行
                if current_key:
                    fields[current_key] += "\n " + line.strip()
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                fields[key.strip()] = val.strip()
                current_key = key.strip()
    return fields

def validate_control(fields):
    """校验 control 必要字段"""
    missing = [f for f in REQUIRED_FIELDS if f not in fields]
    if missing:
        print(f"❌ control 缺少必填字段: {', '.join(missing)}")
        sys.exit(1)
    # 校验版本格式
    ver = fields.get("Version", "")
    if not re.match(r"^[0-9]", ver):
        print(f"⚠️ 版本号 '{ver}' 建议以数字开头")

def collect_files(root_dir):
    """收集"程序安装目录及文件/"下的所有文件（不含 xpm/ 子目录）"""
    files = []
    xpm_dir = os.path.join(root_dir, "xpm")
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 跳过 xpm/ 目录（它是元数据，不是安装内容）
        if os.path.abspath(dirpath).startswith(os.path.abspath(xpm_dir)):
            continue
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root_dir)
            files.append((full, rel))
    return sorted(files)

def write_files_list(files, output_path):
    """写 files.list"""
    with open(output_path, "w") as f:
        for full, rel in files:
            f.write(rel + "\n")

def write_checksums(files, output_path):
    """写 checksums.sha256"""
    with open(output_path, "w") as f:
        for full, rel in files:
            h = hashlib.sha256()
            with open(full, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            f.write(f"{h.hexdigest()}  {rel}\n")

def build_data_tar(files, output_path):
    """打包数据部分（程序安装目录及文件/ 的内容）"""
    with tarfile.open(output_path, "w:gz") as tar:
        for full, rel in files:
            tar.add(full, arcname=rel)

def build_oil_package(root_dir, output_path, sign_key=None):
    """构建最终 .oil 包"""
    xpm_dir = os.path.join(root_dir, "xpm")
    control_path = os.path.join(xpm_dir, "control")

    if not os.path.exists(control_path):
        print(f"❌ 找不到 {control_path}")
        sys.exit(1)

    # 1. 读 control
    fields = read_control(control_path)
    validate_control(fields)

    pkg = fields["Package"]
    ver = fields["Version"]
    arch = fields["Architecture"]

    print(f"🔨 构建: {pkg} {ver} ({arch})")

    # 2. 收集文件
    files = collect_files(root_dir)
    print(f"   📁 文件数: {len(files)}")

    # 3. 生成 files.list
    files_list_path = os.path.join(xpm_dir, "files.list")
    write_files_list(files, files_list_path)

    # 4. 生成 checksums
    checksums_path = os.path.join(xpm_dir, "checksums.sha256")
    write_checksums(files, checksums_path)
    print(f"   ✅ 校验和已生成")

    # 5. 打包 data.tar.gz
    data_tar_path = os.path.join(root_dir, f"{pkg}_{ver}_{arch}.data.tar.gz")
    build_data_tar(files, data_tar_path)
    print(f"   ✅ 数据归档完成")

    # 6. 构建最终 .oil（tar.gz 套 tar.gz）
    oil_path = output_path or f"{pkg}_{ver}_{arch}.oil"
    with tarfile.open(oil_path, "w:gz") as oil:
        # 数据
        oil.add(data_tar_path, arcname="data.tar.gz")
        # 控制文件
        oil.add(control_path, arcname="control")
        oil.add(files_list_path, arcname="files.list")
        oil.add(checksums_path, arcname="checksums.sha256")
        # 脚本
        pmadd = os.path.join(xpm_dir, "pmadd")
        if os.path.isdir(pmadd):
            for script in ["preinst", "postinst", "prerm", "postrm"]:
                sp = os.path.join(pmadd, script)
                if os.path.exists(sp):
                    oil.add(sp, arcname=script)
                    os.chmod(sp, 0o755)

    # 清理临时文件
    os.remove(data_tar_path)

    size = os.path.getsize(oil_path)
    print(f"   ✅ 构建完成: {oil_path} ({size} bytes)")

    # 7. 签名（可选）
    if sign_key:
        sign_oil(oil_path, sign_key)

    return oil_path

def sign_oil(oil_path, key_id):
    """用 GPG 签名 .oil 包"""
    sig_path = oil_path + ".sig"
    try:
        subprocess.run(
            ["gpg", "--detach-sign", "--armor", "--local-user", key_id, oil_path],
            check=True, capture_output=True
        )
        print(f"   ✅ GPG 签名: {sig_path}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"   ⚠️ GPG 签名失败（请确认 gpg 已安装且 key 存在）")

def main():
    parser = argparse.ArgumentParser(
        description="xm-build - XPM 包构建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("directory", help="包含'程序安装目录及文件'的根目录")
    parser.add_argument("--output", "-o", help="输出 .oil 路径")
    parser.add_argument("--sign", help="GPG key ID 用于签名")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    root = os.path.abspath(args.directory)
    if not os.path.isdir(root):
        print(f"❌ 目录不存在: {root}")
        sys.exit(1)

    xpm_dir = os.path.join(root, "xpm")
    if not os.path.isdir(xpm_dir):
        print(f"❌ 缺少 xpm/ 子目录: {xpm_dir}")
        print(f"   目录结构应为:")
        print(f"   {os.path.basename(root)}/")
        print(f"   ├── (程序文件...)")
        print(f"   └── xpm/")
        print(f"       ├── control")
        print(f"       └── pmadd/")
        sys.exit(1)

    oil_path = build_oil_package(root, args.output, args.sign)

    print()
    print(f"🛢️  Oil reserve: 100001%")
    print(f"☕ Build complete. Coffee machine stable.")

if __name__ == "__main__":
    import re
    main()

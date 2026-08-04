#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xpm_build.py - XPM .oil 包构建工具
将目录打包为 .oil（本质是 tar.gz + control + data.tar.gz）
"""

import os
import sys
import tarfile
import hashlib
import gzip
import time
from datetime import datetime

def build_oil(directory):
    """将目录打包为 .oil"""
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        print(f"❌ 目录不存在: {directory}")
        return False
    
    # 读 control
    control_path = os.path.join(directory, "control")
    if not os.path.exists(control_path):
        print(f"❌ 缺少 control 文件: {control_path}")
        return False
    
    control = open(control_path).read()
    
    # 解析包名和版本
    pkg_name = "unknown"
    version = "0"
    for line in control.split("\n"):
        if line.startswith("Package:"):
            pkg_name = line.split(":", 1)[1].strip()
        elif line.startswith("Version:"):
            version = line.split(":", 1)[1].strip()
    
    # 收集文件（排除 control 和 DEBIAN 目录）
    files = []
    for root, dirs, filenames in os.walk(directory):
        rel_root = os.path.relpath(root, directory)
        for f in filenames:
            if f == "control":
                continue
            if rel_root.startswith("DEBIAN"):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, directory)
            files.append((full, rel))
    
    print(f"📦 构建: {pkg_name} ({version})")
    print(f"   文件数: {len(files)}")
    
    # 创建 data.tar.gz
    data_path = f"/tmp/{pkg_name}_data.tar.gz"
    with tarfile.open(data_path, "w:gz") as tar:
        for full, rel in files:
            tar.add(full, arcname=rel)
    
    # 创建 .oil
    oil_path = f"{pkg_name}_{version}.oil"
    with tarfile.open(oil_path, "w:gz") as tar:
        # 添加 control
        tar.add(control_path, arcname="control")
        # 添加 data.tar.gz
        tar.add(data_path, arcname="data.tar.gz")
    
    os.unlink(data_path)
    
    size = os.path.getsize(oil_path)
    print(f"✅ 构建完成: {oil_path} ({size//1024}KB)")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 xpm_build.py <目录>")
        sys.exit(1)
    build_oil(sys.argv[1])

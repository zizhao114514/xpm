#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xm.py - XPM 后端 (eXtended Manager backend)
v2.0-1 - 增强版后端
"""

import os
import sys
import json
import subprocess
import hashlib
import shutil
import tarfile
import gzip
import time
from datetime import datetime

XPM_ROOT = "/opt/xpm"
XPM_DB = f"{XPM_ROOT}/db"
XPM_STATUS = f"{XPM_DB}/status.json"
XPM_CACHE = f"{XPM_ROOT}/cache"
XPM_LOG = f"{XPM_ROOT}/log"

def ensure_dirs():
    for d in [XPM_ROOT, XPM_DB, XPM_CACHE, XPM_LOG]:
        os.makedirs(d, exist_ok=True)

def load_status():
    ensure_dirs()
    try:
        return json.load(open(XPM_STATUS))
    except:
        return {"installed": {}, "version": "2.0-1"}

def save_status(db):
    db["version"] = "2.0-1"
    json.dump(db, open(XPM_STATUS, "w"), indent=2, ensure_ascii=False)

def log(msg):
    ensure_dirs()
    with open(f"{XPM_LOG}/xm.log", "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")

def run_dpkg(args):
    """调用 dpkg"""
    cmd = ["dpkg"] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr

def verify_package(pkg_name):
    """校验包的完整性"""
    db = load_status()
    if pkg_name not in db.get("installed", {}):
        return False, "未安装"
    
    info = db["installed"][pkg_name]
    files = info.get("files", [])
    missing = []
    for f in files:
        if f and not os.path.exists(f):
            missing.append(f)
    
    if missing:
        return False, f"{len(missing)} 个文件缺失"
    return True, "完整"

def list_files(pkg_name):
    """列出包的文件"""
    db = load_status()
    if pkg_name not in db.get("installed", {}):
        return []
    return db["installed"][pkg_name].get("files", [])

def get_disk_usage(pkg_name=None):
    """计算磁盘占用"""
    db = load_status()
    if pkg_name:
        if pkg_name not in db.get("installed", {}):
            return 0
        total = 0
        for f in db["installed"][pkg_name].get("files", []):
            if os.path.exists(f):
                try: total += os.path.getsize(f)
                except: pass
        return total
    else:
        total = 0
        for name, info in db.get("installed", {}).items():
            for f in info.get("files", []):
                if os.path.exists(f):
                    try: total += os.path.getsize(f)
                    except: pass
        return total

def find_file_owner(filepath):
    """查找文件属于哪个包"""
    db = load_status()
    for pkg, info in db.get("installed", {}).items():
        for f in info.get("files", []):
            if f == filepath:
                return pkg
    return None

def check_conflicts(pkg_name):
    """检查文件冲突"""
    db = load_status()
    if pkg_name not in db.get("installed", {}):
        return []
    
    file_set = set(db["installed"][pkg_name].get("files", []))
    conflicts = []
    for other_name, other_info in db.get("installed", {}).items():
        if other_name == pkg_name:
            continue
        other_files = set(other_info.get("files", []))
        overlap = file_set & other_files
        if overlap:
            conflicts.append((other_name, list(overlap)))
    return conflicts

def snapshot():
    """创建当前状态快照"""
    db = load_status()
    tx_id = int(time.time())
    tx_dir = f"{XPM_DB}/transactions/{tx_id}"
    os.makedirs(tx_dir, exist_ok=True)
    with open(f"{tx_dir}/snapshot.json", "w") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    log(f"snapshot created: {tx_id}")
    return tx_id

def restore(tx_id):
    """恢复快照"""
    snap = f"{XPM_DB}/transactions/{tx_id}/snapshot.json"
    if not os.path.exists(snap):
        return False
    db = json.load(open(snap))
    save_status(db)
    log(f"restored: {tx_id}")
    return True

def list_transactions():
    """列出事务"""
    tx_dir = f"{XPM_DB}/transactions"
    if not os.path.isdir(tx_dir):
        return []
    return sorted(os.listdir(tx_dir))

def main():
    if len(sys.argv) < 2:
        print("xm - XPM 后端")
        print("用法: xm <命令> [参数...]")
        return
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    if cmd == "verify":
        for p in args:
            ok, msg = verify_package(p)
            print(f"  {p}: {'✅' if ok else '❌'} {msg}")
    elif cmd == "files":
        if args:
            files = list_files(args[0])
            for f in files:
                print(f)
    elif cmd == "usage":
        if args:
            sz = get_disk_usage(args[0])
        else:
            sz = get_disk_usage()
        print(f"{sz} bytes ({sz//1024}KB)")
    elif cmd == "owns":
        for p in args:
            owner = find_file_owner(p)
            print(f"  {p}: {owner or '未找到'}")
    elif cmd == "conflicts":
        if args:
            confs = check_conflicts(args[0])
            for name, files in confs:
                print(f"  冲突 with {name}: {files[:5]}")
    elif cmd == "snapshot":
        tid = snapshot()
        print(f"快照已创建: #{tid}")
    elif cmd == "restore":
        if args and args[0].isdigit():
            ok = restore(int(args[0]))
            print(f"{'✅' if ok else '❌'} 恢复 {'成功' if ok else '失败'}")
    elif cmd == "transactions":
        for t in list_transactions():
            print(f"  #{t}")
    elif cmd == "status":
        db = load_status()
        print(f"已安装: {len(db.get('installed',{}))} 个包")
        print(f"后端版本: 2.0-1")
    else:
        print(f"未知命令: {cmd}")

if __name__ == "__main__":
    main()

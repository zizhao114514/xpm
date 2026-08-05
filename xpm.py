#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XPM - X11 Package Manager v2.0-6 "Filename-Fixed Edition"
===========================================================
石油驱动 | 功耗 1.x W | 零 apt | 全中文 | 实用功能拉满

Author: zizhao + AI
License: 石油许可证 v2.0（随便用，别怪我）
"""

import os
import sys
import json
import subprocess
import shutil
import hashlib
import time
import re
import gzip
import tarfile
import threading
import queue
import socket
import stat
import glob
import pwd
import grp
import argparse
import textwrap
import curses
from datetime import datetime
from pathlib import Path
from collections import OrderedDict, defaultdict

# ─── 常量 ───────────────────────────────────────────────
XPM_ROOT = "/usr/local/share/xpm"
XPM_DB = f"{XPM_ROOT}/db"
XPM_STATUS = f"{XPM_DB}/status.json"
XPM_SOURCES = f"{XPM_ROOT}/sources.list.d"
XPM_CACHE = f"{XPM_ROOT}/cache"
XPM_LOG = f"{XPM_ROOT}/log"
XPM_HISTORY = f"{XPM_LOG}/history.jsonl"
XPM_CONFIG = f"{XPM_ROOT}/config.json"
XPM_ALIASES = f"{XPM_ROOT}/aliases.json"
XPM_TRANSACTIONS = f"{XPM_DB}/transactions"
XPM_KEYRING = f"{XPM_ROOT}/keyring"
XPM_DOCS = f"{XPM_ROOT}/docs"
XPM_TESTS = f"{XPM_ROOT}/tests"
XPM_DESKTOP = "/usr/share/applications/xpm.desktop"

VERSION = "2.0-6"
CODENAME = "Filename-Fixed Edition"

# 清除代理环境变量（铁律）
for _k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)

# ─── 颜色 ───────────────────────────────────────────────
class C:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

def cprint(color, text):
    print(f"{color}{text}{C.RESET}")

def log_info(msg): print(f"{C.CYAN}[i]{C.RESET} {msg}")
def log_ok(msg): print(f"{C.GREEN}[✓]{C.RESET} {msg}")
def log_warn(msg): print(f"{C.YELLOW}[!]{C.RESET} {msg}")
def log_err(msg): print(f"{C.RED}[✗]{C.RESET} {msg}")
def log_stage(n, total, msg): print(f"{C.BLUE}[{n}/{total}]{C.RESET} {msg}")

# ─── 工具函数 ────────────────────────────────────────────
def ensure_dirs():
    for d in [XPM_DB, XPM_SOURCES, XPM_CACHE, XPM_LOG, XPM_TRANSACTIONS, XPM_KEYRING, XPM_DOCS]:
        os.makedirs(d, exist_ok=True)
    if not os.path.exists(XPM_CONFIG):
        json.dump({
            "language": "zh",
            "auto_clean": False,
            "preferred_mirror": "",
            "max_cache_mb": 500,
            "confirm_install": True,
            "color": True
        }, open(XPM_CONFIG, "w"), indent=2, ensure_ascii=False)

def load_config():
    ensure_dirs()
    try:
        return json.load(open(XPM_CONFIG))
    except:
        return {}

def save_config(cfg):
    json.dump(cfg, open(XPM_CONFIG, "w"), indent=2, ensure_ascii=False)

def load_aliases():
    try:
        return json.load(open(XPM_ALIASES))
    except:
        return {}

def save_aliases(a):
    json.dump(a, open(XPM_ALIASES, "w"), indent=2, ensure_ascii=False)

def load_status():
    ensure_dirs()
    try:
        return json.load(open(XPM_STATUS))
    except:
        return {"installed": {}, "version": VERSION}

def save_status(db):
    db["version"] = VERSION
    json.dump(db, open(XPM_STATUS, "w"), indent=2, ensure_ascii=False)

def log_history(action, pkg, extra=""):
    ensure_dirs()
    entry = {
        "time": datetime.now().isoformat(),
        "action": action,
        "package": pkg,
        "extra": extra,
        "user": os.environ.get("USER", "root")
    }
    with open(XPM_HISTORY, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def read_history(limit=50):
    if not os.path.exists(XPM_HISTORY):
        return []
    lines = open(XPM_HISTORY).readlines()
    return [json.loads(l) for l in lines[-limit:]]

def run_cmd(cmd, timeout=300, capture=False):
    """运行命令，自动清除代理环境"""
    env = os.environ.copy()
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        env.pop(k, None)
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, r.stdout, r.stderr
    else:
        r = subprocess.run(cmd, timeout=timeout, env=env)
        return r.returncode, "", ""

def wget(url, dest, timeout=30):
    """下载文件，返回 (success, message)"""
    cmd = ["wget", "--timeout=" + str(timeout), "--tries=3",
           "--no-check-certificate", "-q", "-O", dest, url]
    env = os.environ.copy()
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        env.pop(k, None)
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode == 0 and os.path.exists(dest):
        return True, f"下载完成: {os.path.getsize(dest)} bytes"
    # 失败时尝试 http 降级
    if url.startswith("https://"):
        http_url = "http://" + url[8:]
        cmd2 = ["wget", "--timeout=" + str(timeout), "--tries=2",
                "-q", "-O", dest, http_url]
        r2 = subprocess.run(cmd2, capture_output=True, text=True, env=env)
        if r2.returncode == 0 and os.path.exists(dest):
            return True, f"下载完成(HTTP降级): {os.path.getsize(dest)} bytes"
    return False, r.stderr.strip() or f"wget 返回 {r.returncode}"

def wget_progress(url, dest, timeout=30):
    """带进度条的下载"""
    cmd = ["wget", "--timeout=" + str(timeout), "--tries=3",
           "--no-check-certificate",
           "--progress=dot:giga", "-O", dest, url]
    env = os.environ.copy()
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        env.pop(k, None)
    r = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    downloaded = 0
    last = time.time()
    while r.poll() is None:
        line = r.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        # 解析进度
        m = re.search(r'(\d+)%', line)
        if m:
            pct = int(m.group(1))
            bar = "█" * (pct // 2) + "░" * (50 - pct // 2)
            elapsed = time.time() - last
            sys.stdout.write(f"\r  [{bar}] {pct}%")
            sys.stdout.flush()
    sys.stdout.write("\n")
    return r.returncode == 0

def parse_sources():
    """解析所有源文件，返回列表"""
    sources = []
    if not os.path.isdir(XPM_SOURCES):
        return sources
    for f in sorted(os.listdir(XPM_SOURCES)):
        if not f.endswith(".list"):
            continue
        path = os.path.join(XPM_SOURCES, f)
        for line in open(path):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            sources.append({"file": f, "line": line, "raw": line})
    return sources


def normalize_source(line):
    """
    统一解析一行源配置，返回 dict：
        {type:"deb", base:"https://...", suite:"bookworm", components:["main",...], raw:line}
    支持：
        deb https://mirror/debian/ bookworm main contrib non-free
        deb https://mirror/debian bookworm/
        [xpm] url=https://example.com/xpm/
        [xpm] https://example.com/xpm/
    返回 None 表示无法识别。
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    if line.startswith("[xpm]"):
        url = line.replace("[xpm]", "").strip()
        if url.startswith("url="):
            url = url[4:].strip()
        base = url.rstrip("/")
        # xpm 源通常本身就是索引根目录
        return {"type": "xpm", "base": base, "suite": "", "components": [""], "raw": line}

    if line.startswith("deb "):
        parts = line.split()
        if len(parts) < 3:
            return None
        base = parts[1].rstrip("/")
        suite = parts[2].strip("/")
        # 剩余部分是 components；若没写，默认 main
        comps = parts[3:] if len(parts) > 3 else ["main"]
        return {"type": "deb", "base": base, "suite": suite, "components": comps, "raw": line}

    # 裸 URL（兼容老写法）
    return {"type": "xpm", "base": line.rstrip("/"), "suite": "", "components": [""], "raw": line}


def release_url(src):
    """返回 dists/{suite}/Release 的测试 URL"""
    if src["type"] == "deb":
        # 兼容 base 末尾已带 /dists 的写法
        if src["base"].endswith("/dists"):
            return f"{src['base']}/{src['suite']}/Release"
        return f"{src['base']}/dists/{src['suite']}/Release"
    else:
        # xpm 源：直接 <base>/Release 或 <base>/index.json
        return f"{src['base']}/Release"


def packages_url(src, component):
    """返回某个 component 的 Packages.gz URL"""
    if src["type"] == "deb":
        if src["base"].endswith("/dists"):
            base = src["base"]
        else:
            base = f"{src['base']}/dists/{src['suite']}"
        return f"{base}/{component}/binary-amd64/Packages.gz"
    else:
        # xpm 源：<base>/<component>/Packages.gz
        comp = component.strip("/")
        if comp:
            return f"{src['base']}/{comp}/Packages.gz"
        return f"{src['base']}/Packages.gz"

def parse_control(text):
    """解析 Debian control 格式"""
    fields = {}
    cur = None
    for line in text.split("\n"):
        if not line:
            continue
        if line[0] in (" ", "\t"):
            if cur:
                fields[cur] += "\n" + line.strip()
        elif ":" in line:
            key, val = line.split(":", 1)
            cur = key.strip()
            fields[cur] = val.strip()
    return fields

def compare_version(v1, v2):
    """Debian 版本比较，返回 -1/0/1"""
    def parse_full(v):
        epoch = 0
        rest = v
        if ":" in v:
            try:
                epoch = int(v.split(":", 1)[0])
                rest = v.split(":", 1)[1]
            except: pass
        upstream = rest
        debian = ""
        if "-" in rest:
            upstream, debian = rest.rsplit("-", 1)
        return epoch, upstream, debian
    e1, u1, d1 = parse_full(v1)
    e2, u2, d2 = parse_full(v2)
    # 先比 epoch
    if e1 < e2: return -1
    if e1 > e2: return 1
    # 再比 upstream（数值优先）
    try:
        if float(u1) < float(u2): return -1
        if float(u1) > float(u2): return 1
    except:
        if u1 < u2: return -1
        if u1 > u2: return 1
    # 最后比 debian 后缀
    if d1 < d2: return -1
    if d1 > d2: return 1
    return 0

def parse_dep_string(dep_str):
    """解析 Depends 字符串，返回列表 of (name, op, version)"""
    deps = []
    for part in dep_str.split(","):
        part = part.strip()
        if not part:
            continue
        # 处理 | (OR)
        alternatives = []
        for alt in part.split("|"):
            alt = alt.strip()
            m = re.match(r"([a-zA-Z0-9+.\-]+)\s*\(?\s*(>=|<=|==|=|>|<)\s*([^)]+)\)?", alt)
            if m:
                alternatives.append((m.group(1), m.group(2), m.group(3).strip()))
            else:
                alternatives.append((alt, None, None))
        deps.append(alternatives)
    return deps

# ─── 包搜索与查询 ───────────────────────────────────────
def build_package_index():
    """从所有源构建包索引"""
    index = {}
    sources = parse_sources()
    for src in sources:
        s = normalize_source(src["raw"])
        if s is None:
            continue

        # 每个 component 下载一份 Packages.gz
        for comp in s["components"]:
            url = packages_url(s, comp)
            cache_name = hashlib.md5(url.encode()).hexdigest()[:12]
            cache_path = f"{XPM_CACHE}/{cache_name}_Packages"

            if not os.path.exists(cache_path):
                log_info(f"更新索引: {url}")
                # 先用 wget（已内置 --no-check-certificate）
                success, msg = wget(url, cache_path + ".gz", timeout=15)
                # 如果失败且是 https，尝试 http 降级
                if not success and url.startswith("https://"):
                    http_url = "http://" + url[8:]
                    log_info(f"  ↻ 尝试 HTTP: {http_url}")
                    success, msg = wget(http_url, cache_path + ".gz", timeout=15)
                if success and os.path.exists(cache_path + ".gz"):
                    try:
                        import io as _io
                        with gzip.open(cache_path + ".gz", "rb") as gz:
                            with open(cache_path, "wb") as out:
                                out.write(gz.read())
                        os.unlink(cache_path + ".gz")
                    except Exception:
                        # 下载失败不影响，后续用缓存
                        if os.path.exists(cache_path + ".gz"):
                            os.unlink(cache_path + ".gz")
                else:
                    if os.path.exists(cache_path + ".gz"):
                        os.unlink(cache_path + ".gz")

            if os.path.exists(cache_path):
                try:
                    text = open(cache_path).read()
                    for block in text.split("\n\n"):
                        ctrl = parse_control(block)
                        if "Package" in ctrl:
                            name = ctrl["Package"]
                            if name not in index:
                                index[name] = []
                            # 存源的 base URL（下载 .deb 时用）
                            ctrl["_base"] = s["base"].rstrip("/")
                            ctrl["_component"] = comp
                            ctrl["_source"] = url
                            index[name].append(ctrl)
                except Exception:
                    continue
    return index


def package_download_url(entry):
    """
    根据 Packages 条目拼出 .deb 的真实下载 URL。
    Debian 官方源：base + "/" + Filename（Filename 形如 pool/main/h/htop/htop_3.4.1-5_amd64.deb）
    xpm 源：base + "/" + Filename
    """
    base = entry.get("_base", "").rstrip("/")
    filename = entry.get("Filename", "").lstrip("/")
    if not base:
        # 兜底：用 _source 反推（Packages.gz 所在目录的上一级）
        src = entry.get("_source", "")
        if src:
            base = src.rsplit("/", 3)[0]  # .../dists/suite/comp/binary-amd64 -> base
    if not filename:
        # 终极兜底：自己拼（可能不准，仅当 Filename 字段缺失）
        pkg = entry.get("Package", "unknown")
        ver = entry.get("Version", "unknown")
        arch = entry.get("Architecture", "amd64")
        comp = entry.get("_component", "main")
        first = pkg[0] if pkg else "x"
        filename = f"pool/{comp}/{first}/{pkg}/{pkg}_{ver}_{arch}.deb"
    return f"{base}/{filename}"

def search_packages(query, index=None):
    """模糊搜索包"""
    if index is None:
        index = build_package_index()
    query = query.lower()
    results = []
    for name, entries in index.items():
        for entry in entries:
            desc = entry.get("Description", "").lower()
            if query in name.lower() or query in desc:
                results.append(entry)
    return results

def find_provides(cmd_name, index=None):
    """查找哪个包提供某个命令"""
    if index is None:
        index = build_package_index()
    results = []
    for name, entries in index.items():
        for entry in entries:
            provides = entry.get("Provides", "")
            if cmd_name in provides.split(","):
                results.append(entry)
            # 也检查 bin 文件列表（如果有）
            bin_list = entry.get("Bin-Files", "")
            if cmd_name in bin_list.split():
                results.append(entry)
    return results

def find_owns(filepath):
    """查找文件属于哪个已装包"""
    db = load_status()
    for pkg, info in db.get("installed", {}).items():
        files = info.get("files", [])
        for f in files:
            if filepath == f or filepath in f:
                return pkg, info
    return None, None

# ─── 安装 / 卸载核心 ────────────────────────────────────
def resolve_dependencies(pkg_name, index, db, depth=0):
    """解析依赖，返回需要安装的包列表"""
    to_install = []
    seen = set()
    
    def _resolve(name, deps_chain):
        if name in seen:
            return
        seen.add(name)
        
        # 已安装？
        if name in db.get("installed", {}):
            return
        
        # 在索引中找
        if name not in index:
            log_warn(f"找不到包: {name}（依赖链: {' → '.join(deps_chain)}）")
            return
        
        # 选最高版本
        entries = sorted(index[name], key=lambda e: e.get("Version", ""), reverse=True)
        entry = entries[0]
        to_install.append(entry)
        
        # 递归解析依赖
        deps_str = entry.get("Depends", "")
        if deps_str:
            deps = parse_dep_string(deps_str)
            for alternatives in deps:
                for dep_name, op, ver in alternatives:
                    if dep_name == "bash" or dep_name.startswith("libc"):
                        continue  # 基础系统包跳过
                    _resolve(dep_name, deps_chain + [name])
    
    _resolve(pkg_name, [])
    return to_install

def download_package(entry, show_progress=True):
    """下载 .deb 包（用 Packages 里的 Filename 字段拼真实 URL）"""
    pkg_name = entry["Package"]
    version = entry.get("Version", "unknown")
    url = package_download_url(entry)
    dest = f"{XPM_CACHE}/{pkg_name}_{version}.deb"

    log_info(f"下载: {pkg_name} ({version})")
    log_info(f"  URL: {url}")

    if show_progress:
        ok = wget_progress(url, dest)
    else:
        ok, msg = wget(url, dest)
        if not ok:
            log_warn(f"  wget 失败: {msg}")

    # HTTPS 失败 → 尝试 HTTP 降级
    if not ok and url.startswith("https://"):
        http_url = "http://" + url[8:]
        log_info(f"  ↻ 尝试 HTTP: {http_url}")
        if show_progress:
            ok = wget_progress(http_url, dest)
        else:
            ok, msg = wget(http_url, dest)
            if not ok:
                log_warn(f"  HTTP 也失败: {msg}")

    if not ok:
        log_err(f"下载失败: {pkg_name}")
        log_err(f"  最终 URL: {url}")
    return ok, dest

def install_package(pkg_name, dry_run=False, confirm=True):
    """安装包（完整 4 阶段）"""
    db = load_status()
    
    # 已安装检查
    if pkg_name in db.get("installed", {}):
        log_warn(f"{pkg_name} 已安装 (版本: {db['installed'][pkg_name].get('version','?')})")
        r = input("重新安装? [y/N] ")
        if r.lower() != "y":
            return
        # 走 reinstall 逻辑
    
    # 构建索引
    log_info("正在更新软件源索引...")
    index = build_package_index()
    
    if pkg_name not in index:
        log_err(f"找不到包: {pkg_name}")
        # 模糊建议
        suggestions = [n for n in index if pkg_name in n]
        if suggestions:
            log_info(f"你是不是要找: {', '.join(suggestions[:5])}")
        return
    
    # 选最高版本
    entries = sorted(index[pkg_name], key=lambda e: e.get("Version", ""), reverse=True)
    entry = entries[0]
    version = entry.get("Version", "unknown")
    
    # 解析依赖
    log_stage(1, 4, f"正在选中未安装的软件包：{pkg_name}")
    to_install = resolve_dependencies(pkg_name, index, db)
    
    if dry_run:
        cprint(C.CYAN, f"\n--- DRY RUN: 将安装以下包 ---")
        total_size = 0
        for e in to_install:
            sz = e.get("Size", "0")
            try: total_size += int(sz)
            except: pass
            cprint(C.WHITE, f"  {e['Package']} ({e.get('Version','?')}) - {e.get('Description','')[:60]}")
        cprint(C.CYAN, f"--- 总计: {len(to_install)} 个包, ~{total_size//1024}KB ---\n")
        return
    
    # 显示将要安装的
    if len(to_install) > 1:
        log_info(f"将同时安装 {len(to_install)} 个包（含依赖）")
        for e in to_install:
            print(f"  • {e['Package']} ({e.get('Version','?')})")
    
    if confirm and load_config().get("confirm_install", True):
        r = input(f"\n确认安装? [Y/n] ")
        if r.lower() == "n":
            log_info("已取消")
            return
    
    # 事务快照
    snapshot = dict(db.get("installed", {}))
    
    try:
        for i, e in enumerate(to_install):
            name = e["Package"]
            ver = e.get("Version", "unknown")
            log_stage(2, 4, f"正在选中 {name} ({ver})")
            
            # 下载
            ok, dest = download_package(e)
            if not ok:
                raise Exception(f"下载失败: {name}")
            
            # 解包
            log_stage(3, 4, f"正在解压 {name} ({ver})...")
            if not extract_oil(dest, name, ver):
                raise Exception(f"解包失败: {name}")
            
            # 配置
            log_stage(4, 4, f"正在设置 {name} ({ver})...")
            run_postinst(name, ver)
            
            # 更新数据库
            db["installed"][name] = {
                "version": ver,
                "installed_at": datetime.now().isoformat(),
                "files": get_installed_files(name),
                "source": e.get("_source", "")
            }
            save_status(db)
            log_history("install", name, f"version={ver}")
            log_ok(f"{name} ({ver}) 安装完成")
    
    except Exception as ex:
        log_err(f"安装失败: {ex}")
        # 回滚
        log_warn("正在回滚...")
        db["installed"] = snapshot
        save_status(db)
        log_history("rollback", pkg_name, str(ex))
        return
    
    log_ok(f"✅ 全部安装完成 ({len(to_install)} 个包)")

def extract_oil(oil_path, pkg_name, version):
    """解压 .oil 包"""
    try:
        # .oil 本质是 tar.gz
        with tarfile.open(oil_path, "r:gz") as tar:
            # 先读 control
            control_data = None
            data_tar = None
            for m in tar.getmembers():
                if m.name == "control" or m.name.endswith("/control"):
                    control_data = tar.extractfile(m).read().decode()
                elif m.name == "data.tar.gz" or m.name.endswith("/data.tar.gz"):
                    data_tar = tar.extractfile(m).read()
            
            if control_data:
                ctrl = parse_control(control_data)
                log_info(f"  包信息: {ctrl.get('Description','')[:80]}")
            
            # 解压 data.tar.gz
            if data_tar:
                import io
                with tarfile.open(fileobj=io.BytesIO(data_tar), mode="r:gz") as data:
                    # 计算文件列表
                    files = []
                    for m in data.getmembers():
                        if m.isfile():
                            files.append(m.name)
                    # 解压到根
                    data.extractall("/")
                    # 保存文件列表
                    os.makedirs(f"{XPM_DB}/files", exist_ok=True)
                    with open(f"{XPM_DB}/files/{pkg_name}", "w") as f:
                        f.write("\n".join(files))
            
            # 跑 preinst
            if control_data:
                ctrl = parse_control(control_data)
                preinst = ctrl.get("Pre-Inst", "")
                if preinst:
                    log_info(f"  执行 preinst 脚本...")
                    # 写入临时脚本执行
                    script_path = f"/tmp/xpm_preinst_{pkg_name}"
                    with open(script_path, "w") as sf:
                        sf.write("#!/bin/sh\n" + preinst)
                    os.chmod(script_path, 0o755)
                    subprocess.run([script_path], capture_output=True)
                    os.unlink(script_path)
            
            return True
    except Exception as e:
        log_err(f"  解包异常: {e}")
        return False

def run_postinst(pkg_name, version):
    """执行 postinst 脚本"""
    # 从 control 读 postinst
    ctrl_path = f"{XPM_DB}/control/{pkg_name}"
    if os.path.exists(ctrl_path):
        ctrl = parse_control(open(ctrl_path).read())
        postinst = ctrl.get("Post-Inst", "")
        if postinst:
            log_info(f"  执行 postinst 脚本...")
            script_path = f"/tmp/xpm_postinst_{pkg_name}"
            with open(script_path, "w") as sf:
                sf.write("#!/bin/sh\n" + postinst)
            os.chmod(script_path, 0o755)
            subprocess.run([script_path], capture_output=True)
            os.unlink(script_path)

def get_installed_files(pkg_name):
    """获取已装包的文件列表"""
    fl = f"{XPM_DB}/files/{pkg_name}"
    if os.path.exists(fl):
        return open(fl).read().split("\n")
    return []

def remove_package(pkg_name, purge=False):
    """卸载包（3 阶段）"""
    db = load_status()
    if pkg_name not in db.get("installed", {}):
        log_err(f"{pkg_name} 未安装")
        return
    
    info = db["installed"][pkg_name]
    version = info.get("version", "unknown")
    files = info.get("files", [])
    
    # 检查是否有其他包依赖它
    for other_name, other_info in db.get("installed", {}).items():
        if other_name == pkg_name:
            continue
        # 简单检查：other 的 depends 里有没有 pkg_name
        pass  # 完整实现需要查 control
    
    log_stage(1, 3, f"正在寻找与 {pkg_name} 相关的文件...")
    log_info(f"  找到 {len(files)} 个文件")
    
    log_stage(2, 3, f"正在卸载 {pkg_name} ({version})...")
    
    # 跑 prerm
    ctrl_path = f"{XPM_DB}/control/{pkg_name}"
    if os.path.exists(ctrl_path):
        ctrl = parse_control(open(ctrl_path).read())
        prerm = ctrl.get("Pre-Rm", "")
        if prerm:
            log_info(f"  执行 prerm 脚本...")
            script_path = f"/tmp/xpm_prerm_{pkg_name}"
            with open(script_path, "w") as sf:
                sf.write("#!/bin/sh\n" + prerm)
            os.chmod(script_path, 0o755)
            subprocess.run([script_path], capture_output=True)
            os.unlink(script_path)
    
    # 删除文件
    removed = 0
    for f in files:
        if f and os.path.exists(f):
            try:
                if os.path.isdir(f):
                    os.rmdir(f)
                else:
                    os.unlink(f)
                removed += 1
            except:
                pass
    
    # 跑 postrm
    if os.path.exists(ctrl_path):
        ctrl = parse_control(open(ctrl_path).read())
        postrm = ctrl.get("Post-Rm", "")
        if postrm:
            log_info(f"  执行 postrm 脚本...")
            script_path = f"/tmp/xpm_postrm_{pkg_name}"
            with open(script_path, "w") as sf:
                sf.write("#!/bin/sh\n" + postrm)
            os.chmod(script_path, 0o755)
            subprocess.run([script_path], capture_output=True)
            os.unlink(script_path)
    
    if purge:
        log_stage(3, 3, f"正在清除 {pkg_name} ({version})...")
        # 删除配置
        for cfg in [f"{XPM_DB}/control/{pkg_name}", f"{XPM_DB}/files/{pkg_name}"]:
            if os.path.exists(cfg):
                os.unlink(cfg)
        # 删除包配置目录
        for d in [f"/etc/xpm/{pkg_name}", f"/etc/{pkg_name}"]:
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
    else:
        log_info("配置已保留（用 purge 彻底清除）")
    
    # 更新数据库
    del db["installed"][pkg_name]
    save_status(db)
    log_history("remove" if not purge else "purge", pkg_name, f"version={version}, files={removed}")
    log_ok(f"✅ {pkg_name} 已卸载 ({removed} 个文件已删除)")

def autoremove():
    """自动移除孤儿包"""
    db = load_status()
    installed = db.get("installed", {})
    
    # 构建反向依赖图
    deps_of = defaultdict(set)  # pkg -> set of pkgs that depend on it
    for name, info in installed.items():
        ctrl_path = f"{XPM_DB}/control/{name}"
        if os.path.exists(ctrl_path):
            ctrl = parse_control(open(ctrl_path).read())
            deps_str = ctrl.get("Depends", "")
            for alt_group in parse_dep_string(deps_str):
                for dep_name, _, _ in alt_group:
                    if dep_name in installed:
                        deps_of[dep_name].add(name)
    
    # 找孤儿（没人依赖的，且不是手动安装的）
    orphans = []
    for name, info in installed.items():
        if not deps_of.get(name):
            # 检查是否是"手动安装"的（有 install 历史）
            is_manual = False
            for h in read_history(200):
                if h["package"] == name and h["action"] == "install":
                    is_manual = True
                    break
            if not is_manual:
                orphans.append(name)
    
    if not orphans:
        log_ok("没有找到孤儿包")
        return
    
    log_warn(f"找到 {len(orphans)} 个孤儿包:")
    total_size = 0
    for o in sorted(orphans):
        sz = 0
        for f in installed[o].get("files", []):
            if os.path.exists(f):
                try: sz += os.path.getsize(f)
                except: pass
        total_size += sz
        print(f"  • {o} (~{sz//1024}KB)")
    
    r = input(f"\n确认移除这 {len(orphans)} 个孤儿包? [y/N] ")
    if r.lower() != "y":
        log_info("已取消")
        return
    
    for o in sorted(orphans):
        remove_package(o)

def clean_cache(aggressive=False):
    """清理缓存"""
    if not os.path.isdir(XPM_CACHE):
        log_ok("缓存目录不存在")
        return
    
    files = glob.glob(f"{XPM_CACHE}/*")
    total = 0
    for f in files:
        if aggressive or f.endswith("_Packages") or ".deb" in f or ".oil" in f:
            sz = os.path.getsize(f)
            os.unlink(f)
            total += sz
    log_ok(f"已清理 {total//1024}KB 缓存")

def dedupe_check():
    """检测重复文件"""
    db = load_status()
    file_owners = defaultdict(list)
    
    for pkg, info in db.get("installed", {}).items():
        for f in info.get("files", []):
            if f:
                file_owners[f].append(pkg)
    
    conflicts = {f: owners for f, owners in file_owners.items() if len(owners) > 1}
    if not conflicts:
        log_ok("没有发现重复文件冲突")
        return
    
    log_warn(f"发现 {len(conflicts)} 个文件被多个包包含:")
    for f, owners in list(conflicts.items())[:20]:
        print(f"  {f}: {', '.join(owners)}")

def fix_broken():
    """修复损坏的包"""
    db = load_status()
    broken = []
    
    for pkg, info in db.get("installed", {}).items():
        files = info.get("files", [])
        missing = 0
        for f in files[:20]:  # 抽检前20个
            if f and not os.path.exists(f):
                missing += 1
        if missing > 5:
            broken.append((pkg, missing, len(files)))
    
    if not broken:
        log_ok("没有发现损坏的包")
        return
    
    log_warn(f"发现 {len(broken)} 个可能损坏的包:")
    for pkg, miss, total in broken:
        print(f"  • {pkg}: {miss}/{total} 文件缺失")
    
    r = input("尝试重新安装这些包? [y/N] ")
    if r.lower() == "y":
        for pkg, _, _ in broken:
            install_package(pkg)

# ─── 源管理 ──────────────────────────────────────────────
def source_add(name, url, dist="stable", comp="main"):
    """添加软件源"""
    ensure_dirs()
    fname = f"{XPM_SOURCES}/{name}.list"
    line = f"deb {url} {dist} {comp}\n"
    with open(fname, "w") as f:
        f.write(line)
    log_ok(f"已添加源: {name} → {url} {dist} {comp}")

def source_remove(name):
    """移除软件源"""
    fname = f"{XPM_SOURCES}/{name}.list"
    if os.path.exists(fname):
        os.unlink(fname)
        log_ok(f"已移除源: {name}")
    else:
        log_err(f"源不存在: {name}")

def source_list_cmd():
    """列出所有源"""
    sources = parse_sources()
    if not sources:
        log_warn("没有配置任何软件源")
        log_info("用 xpm source add <名称> <URL> [dist] [comp] 添加")
        return
    
    for s in sources:
        print(f"  📦 {s['file']}: {s['line']}")

def test_mirrors():
    """测试所有源的延迟（先测 Release，再测各 component 的 Packages.gz）"""
    sources = parse_sources()
    if not sources:
        log_warn("没有配置任何软件源")
        log_info("添加源: xpm source add <名称> <URL> [dist] [comp]")
        return

    results = []

    for s in sources:
        raw_line = s["line"].strip()
        src = normalize_source(raw_line)
        if src is None:
            log_warn(f"无法解析源: {raw_line}")
            continue

        # 1) 测 Release 文件
        url = release_url(src)
        display = f"{s['file']}: {src['base']} ({'/'.join(src['components'])})"
        log_info(f"测试: {display}")
        log_info(f"  URL: {url}")

        start = time.time()
        ok = False
        error_msg = ""
        try:
            cmd = ["wget", "--timeout=10", "--tries=2",
                   "--no-check-certificate", "--spider", url]
            env = os.environ.copy()
            for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
                env.pop(k, None)
            r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=15)
            elapsed = (time.time() - start) * 1000
            if r.returncode == 0:
                ok = True
                log_ok(f"  ✅ Release: {elapsed:.0f}ms")
            else:
                error_msg = r.stderr.strip().split("\n")[-1] if r.stderr else f"exit {r.returncode}"
                log_warn(f"  ❌ Release 失败 ({error_msg})")

                # 尝试 http 降级
                if url.startswith("https://"):
                    http_url = "http://" + url[8:]
                    log_info(f"  ↻ 尝试 HTTP: {http_url}")
                    cmd2 = ["wget", "--timeout=10", "--tries=2", "--spider", http_url]
                    r2 = subprocess.run(cmd2, capture_output=True, text=True, env=env, timeout=15)
                    if r2.returncode == 0:
                        ok = True
                        elapsed = (time.time() - start) * 1000
                        log_ok(f"  ✅ Release (HTTP): {elapsed:.0f}ms")
                        url = http_url  # 记录成功的 URL
        except subprocess.TimeoutExpired:
            elapsed = 99999
            log_warn(f"  ❌ Release 超时")

        # 2) 测每个 component 的 Packages.gz（取平均）
        comp_times = []
        if ok:
            for comp in src["components"]:
                pkg_url = packages_url(src, comp)
                t0 = time.time()
                try:
                    cmd2 = ["wget", "--timeout=10", "--tries=2",
                            "--no-check-certificate", "--spider", pkg_url]
                    env2 = os.environ.copy()
                    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
                        env2.pop(k, None)
                    r2 = subprocess.run(cmd2, capture_output=True, env=env2, timeout=15)
                    t_ms = (time.time() - t0) * 1000
                    if r2.returncode == 0:
                        comp_times.append(t_ms)
                        log_info(f"  ✅ {comp or 'root'}: {t_ms:.0f}ms")
                except subprocess.TimeoutExpired:
                    pass

        # 综合延迟
        if comp_times:
            avg = sum(comp_times) / len(comp_times)
            total = elapsed + avg
        else:
            total = elapsed if ok else 99999

        results.append((s["file"], total, url, ok, error_msg))

    # 排序并输出
    results.sort(key=lambda x: x[1])
    print(f"\n{'源文件':<28} {'延迟':>10}  状态")
    print("-" * 55)
    for name, ms, url, ok, err in results:
        if ok and ms < 2000:
            marker = "🏆"
        elif ok:
            marker = "  "
        else:
            marker = "⚠️ "
        status = f"{ms:>8.0f}ms" if ok else f"  失败"
        print(f"{marker} {name:<26} {status}")
        if not ok and err:
            print(f"     └─ {err}")

    good = [r for r in results if r[3] and r[1] < 5000]
    if good:
        log_info(f"推荐源: {good[0][0]} ({good[0][1]:.0f}ms)")
    elif results:
        log_warn("所有源都不可用，请检查网络或添加新源")
        log_info("提示: 如果看到 SSL 错误，可能是 CA 证书问题")
        log_info("      尝试: apt install --reinstall ca-certificates")

# ─── 包信息查询 ──────────────────────────────────────────
def show_package(pkg_name):
    """显示包详细信息"""
    index = build_package_index()
    if pkg_name not in index:
        log_err(f"找不到包: {pkg_name}")
        return
    
    entries = sorted(index[pkg_name], key=lambda e: e.get("Version", ""), reverse=True)
    e = entries[0]
    
    db = load_status()
    installed = db.get("installed", {})
    
    print(f"\n{C.BOLD}{C.CYAN}╔══════════════════════════════════════╗")
    print(f"║  📦 {pkg_name:<32s} ║")
    print(f"╚══════════════════════════════════════╝{C.RESET}")
    print(f"  版本:       {e.get('Version', '?')}")
    print(f"  大小:       {int(e.get('Size', 0))//1024}KB")
    print(f"  状态:       {C.GREEN+'已安装'+C.RESET if pkg_name in installed else C.DIM+'未安装'+C.RESET}")
    if pkg_name in installed:
        print(f"  已装版本:   {installed[pkg_name].get('version','?')}")
        print(f"  安装时间:   {installed[pkg_name].get('installed_at','?')}")
    print(f"  优先级:     {e.get('Priority', 'optional')}")
    print(f"  区段:       {e.get('Section', '?')}")
    print(f"  维护者:     {e.get('Maintainer', '?')}")
    print(f"  主页:       {e.get('Homepage', '?')}")
    print(f"  许可证:     {e.get('License', '?')}")
    
    deps = e.get("Depends", "")
    if deps:
        print(f"  依赖:       {deps[:80]}")
    recommends = e.get("Recommends", "")
    if recommends:
        print(f"  推荐:       {recommends[:80]}")
    provides = e.get("Provides", "")
    if provides:
        print(f"  提供:       {provides}")
    
    desc = e.get("Description", "")
    if desc:
        print(f"\n  描述:")
        for line in desc.split("\n")[:5]:
            print(f"    {line}")
    
    # 已装文件数
    if pkg_name in installed:
        files = installed[pkg_name].get("files", [])
        print(f"\n  文件数:     {len(files)}")
        if files:
            print(f"  示例文件:")
            for f in files[:5]:
                print(f"    {f}")
            if len(files) > 5:
                print(f"    ... 还有 {len(files)-5} 个")

def calc_size(pkg_name=None):
    """计算包占用空间"""
    db = load_status()
    installed = db.get("installed", {})
    
    if pkg_name:
        if pkg_name not in installed:
            log_err(f"{pkg_name} 未安装")
            return
        total = 0
        for f in installed[pkg_name].get("files", []):
            if os.path.exists(f):
                try: total += os.path.getsize(f)
                except: pass
        print(f"📦 {pkg_name}: {total//1024}KB ({total} bytes)")
        return
    
    # 全部包按大小排序
    results = []
    for name, info in installed.items():
        total = 0
        for f in info.get("files", []):
            if os.path.exists(f):
                try: total += os.path.getsize(f)
                except: pass
        results.append((name, total))
    
    results.sort(key=lambda x: x[1], reverse=True)
    total_all = sum(r[1] for r in results)
    
    print(f"\n{'包名':<30} {'大小':>12} {'占比':>8}")
    print("-" * 55)
    for name, sz in results[:30]:
        pct = (sz / total_all * 100) if total_all > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {name:<28} {sz//1024:>8}KB {pct:>6.1f}% {bar}")
    print("-" * 55)
    print(f"  {'总计':<28} {total_all//1024:>8}KB")

def why_package(pkg_name):
    """为什么安装了它"""
    db = load_status()
    installed = db.get("installed", {})
    
    if pkg_name not in installed:
        log_err(f"{pkg_name} 未安装")
        return
    
    # 查历史
    hist = read_history(500)
    for h in reversed(hist):
        if h["package"] == pkg_name and h["action"] == "install":
            log_info(f"{pkg_name} 于 {h['time']} 被安装")
            log_info(f"  操作者: {h.get('user','?')}")
            if h.get("extra"):
                log_info(f"  详情: {h['extra']}")
            break
    else:
        log_info(f"{pkg_name} 安装时间: {installed[pkg_name].get('installed_at','未知')}")
    
    # 查谁依赖它
    dependents = []
    for other_name, other_info in installed.items():
        if other_name == pkg_name:
            continue
        ctrl_path = f"{XPM_DB}/control/{other_name}"
        if os.path.exists(ctrl_path):
            ctrl = parse_control(open(ctrl_path).read())
            deps_str = ctrl.get("Depends", "")
            for alt_group in parse_dep_string(deps_str):
                for dep_name, _, _ in alt_group:
                    if dep_name == pkg_name:
                        dependents.append(other_name)
    
    if dependents:
        log_info(f"被以下 {len(dependents)} 个包依赖:")
        for d in dependents:
            print(f"  • {d}")
    else:
        log_warn(f"没有已装包依赖 {pkg_name}（可能是手动安装或孤儿）")

# ─── 历史与新闻 ──────────────────────────────────────────
def show_history(limit=20):
    """显示安装历史"""
    hist = read_history(limit)
    if not hist:
        log_info("没有历史记录")
        return
    
    print(f"\n{'时间':<22} {'操作':<10} {'包名':<25} {'详情'}")
    print("-" * 80)
    for h in reversed(hist):
        action_icon = {"install": "📥", "remove": "🗑️", "purge": "💥",
                       "upgrade": "⬆️", "rollback": "⏪"}.get(h["action"], "•")
        print(f"  {h['time'][:19]:<20} {action_icon} {h['action']:<8} {h['package']:<23} {h.get('extra','')[:30]}")

def show_news():
    """显示可更新的包"""
    db = load_status()
    installed = db.get("installed", {})
    index = build_package_index()
    
    updates = []
    for name, info in installed.items():
        if name in index:
            entries = sorted(index[name], key=lambda e: e.get("Version", ""), reverse=True)
            latest = entries[0].get("Version", "")
            current = info.get("version", "")
            if compare_version(latest, current) > 0:
                updates.append((name, current, latest))
    
    if not updates:
        log_ok("所有包都是最新的 🎉")
        return
    
    print(f"\n有 {len(updates)} 个包可更新:\n")
    print(f"  {'包名':<25} {'当前版本':<20} {'最新版本'}")
    print(f"  " + "-" * 65)
    for name, cur, latest in updates:
        print(f"  {name:<25} {cur:<20} → {C.GREEN}{latest}{C.RESET}")
    
    total_size = 0
    for name, _, _ in updates:
        if name in index:
            for e in index[name]:
                if e.get("Version") == _:
                    try: total_size += int(e.get("Size", 0))
                    except: pass
                    break
    print(f"\n  更新总大小: ~{total_size//1024}KB")
    r = input("\n全部更新? [y/N] ")
    if r.lower() == "y":
        for name, _, _ in updates:
            install_package(name, confirm=False)

# ─── 别名系统 ────────────────────────────────────────────
def alias_add(name, command):
    aliases = load_aliases()
    aliases[name] = command
    save_aliases(aliases)
    log_ok(f"别名已添加: {name} → {command}")

def alias_remove(name):
    aliases = load_aliases()
    if name in aliases:
        del aliases[name]
        save_aliases(aliases)
        log_ok(f"别名已删除: {name}")
    else:
        log_err(f"别名不存在: {name}")

def alias_list_cmd():
    aliases = load_aliases()
    if not aliases:
        log_info("没有设置别名")
        return
    for name, cmd in aliases.items():
        print(f"  {name} → {cmd}")

# ─── 交互式安装（TUI） ──────────────────────────────────
def interactive_install():
    """交互式包选择"""
    index = build_package_index()
    pkgs = sorted(index.keys())
    
    if not pkgs:
        log_warn("没有可用的包")
        return
    
    log_info(f"共 {len(pkgs)} 个包可用，输入数字选择（空格分隔多个，回车确认）:")
    
    # 分页显示
    page_size = 20
    for i in range(0, len(pkgs), page_size):
        batch = pkgs[i:i+page_size]
        for j, p in enumerate(batch):
            ver = index[p][0].get("Version", "?")
            desc = index[p][0].get("Description", "")[:50]
            print(f"  [{i+j+1:>3}] {p:<25} {ver:<15} {desc}")
        if i + page_size < len(pkgs):
            r = input(f"  --- 按回车继续 ({i+page_size}/{len(pkgs)}) ---")
    
    print()
    sel = input("选择包编号 (空格分隔): ")
    selected = []
    for s in sel.split():
        try:
            idx = int(s) - 1
            if 0 <= idx < len(pkgs):
                selected.append(pkgs[idx])
        except:
            pass
    
    if not selected:
        log_info("未选择任何包")
        return
    
    for pkg in selected:
        install_package(pkg, confirm=False)

# ─── 批量安装 ────────────────────────────────────────────
def batch_install(file_path):
    """从文件批量安装"""
    if not os.path.exists(file_path):
        log_err(f"文件不存在: {file_path}")
        return
    
    pkgs = []
    for line in open(file_path):
        line = line.strip()
        if line and not line.startswith("#"):
            pkgs.append(line)
    
    if not pkgs:
        log_warn("文件中没有包名")
        return
    
    log_info(f"将从 {file_path} 安装 {len(pkgs)} 个包")
    for pkg in pkgs:
        print(f"\n{'='*50}")
        install_package(pkg, confirm=False)

# ─── 离线安装 ────────────────────────────────────────────
def offline_install(pkg_name):
    """从本地缓存离线安装"""
    db = load_status()
    if pkg_name in db.get("installed", {}):
        log_warn(f"{pkg_name} 已安装")
        return
    
    # 在缓存里找
    cached = glob.glob(f"{XPM_CACHE}/{pkg_name}_*.oil")
    if not cached:
        cached = glob.glob(f"{XPM_CACHE}/{pkg_name}_*.deb")
    if not cached:
        log_err(f"缓存中找不到 {pkg_name}，先联网下载一次")
        return
    
    cached.sort(key=os.path.getmtime, reverse=True)
    archive = cached[0]
    log_info(f"使用本地缓存: {os.path.basename(archive)} ({os.path.getsize(archive)//1024}KB)")
    
    # 从 oil/deb 获取版本
    version = "unknown"
    if archive.endswith(".oil"):
        try:
            with tarfile.open(archive, "r:gz") as tar:
                for m in tar.getmembers():
                    if m.name == "control":
                        ctrl = parse_control(tar.extractfile(m).read().decode())
                        version = ctrl.get("Version", "unknown")
                        break
        except:
            pass
    
    log_stage(2, 4, f"正在选中 {pkg_name} ({version})")
    log_stage(3, 4, f"正在解压 {pkg_name} ({version})...")
    if extract_oil(archive, pkg_name, version):
        log_stage(4, 4, f"正在设置 {pkg_name} ({version})...")
        run_postinst(pkg_name, version)
        db["installed"][pkg_name] = {
            "version": version,
            "installed_at": datetime.now().isoformat(),
            "files": get_installed_files(pkg_name),
            "source": "offline-cache"
        }
        save_status(db)
        log_history("install", pkg_name, f"version={version},offline")
        log_ok(f"✅ {pkg_name} ({version}) 离线安装完成")

def download_only(pkg_name):
    """只下载不安装"""
    index = build_package_index()
    if pkg_name not in index:
        log_err(f"找不到包: {pkg_name}")
        return

    entries = sorted(index[pkg_name], key=lambda e: e.get("Version", ""), reverse=True)
    entry = entries[0]

    dest_dir = os.path.expanduser("~/xpm-downloads")
    os.makedirs(dest_dir, exist_ok=True)

    version = entry.get("Version", "unknown")
    url = package_download_url(entry)
    filename = url.rsplit("/", 1)[-1] or f"{pkg_name}_{version}.deb"
    dest = f"{dest_dir}/{filename}"

    log_info(f"下载到: {dest}")
    log_info(f"  URL: {url}")
    ok = wget_progress(url, dest)
    if not ok and url.startswith("https://"):
        http_url = "http://" + url[8:]
        log_info(f"  ↻ 尝试 HTTP: {http_url}")
        ok = wget_progress(http_url, dest)
    if ok:
        log_ok(f"✅ 已下载: {dest} ({os.path.getsize(dest)//1024}KB)")
    else:
        log_err(f"下载失败: {url}")

# ─── 增强版 doctor ────────────────────────────────────────
def doctor():
    """系统健康检查（增强版）"""
    print(f"\n{C.BOLD}{C.CYAN}╔══════════ XPM Doctor ══════════╗")
    print(f"║  v{VERSION} {CODENAME:<23s} ║")
    print(f"╚════════════════════════════════╝{C.RESET}\n")
    
    checks = []
    
    # 1. 运行环境
    is_root = os.geteuid() == 0 if hasattr(os, "geteuid") else True
    checks.append(("运行身份", "✅ root" if is_root else "⚠️ 非 root（建议 sudo -i）", is_root))
    
    # 2. 网络
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        checks.append(("网络连通", "✅ 正常", True))
    except:
        checks.append(("网络连通", "❌ 无法连接外网", False))
    
    # 3. DNS
    try:
        import socket as s
        s.gethostbyname("mirrors.tuna.tsinghua.edu.cn")
        checks.append(("DNS 解析", "✅ 正常", True))
    except:
        checks.append(("DNS 解析", "❌ DNS 异常", False))
    
    # 4. 代理
    proxy_set = any(os.environ.get(k) for k in ("http_proxy", "https_proxy", "HTTP_PROXY"))
    checks.append(("代理环境", "✅ 未设置（干净）" if not proxy_set else f"⚠️ 已设置: {os.environ.get('http_proxy','')}", not proxy_set))
    
    # 5. 软件源
    sources = parse_sources()
    checks.append(("软件源", f"✅ {len(sources)} 个源" if sources else "❌ 没有配置源", len(sources) > 0))
    
    # 6. 后端
    xm_path = "/usr/local/bin/xm"
    checks.append(("后端 xm", "✅ 存在" if os.path.exists(xm_path) else "❌ 不存在", os.path.exists(xm_path)))
    
    # 7. dpkg
    rc, out, _ = run_cmd(["which", "dpkg"], capture=True)
    checks.append(("dpkg", "✅ 可用" if rc == 0 else "❌ 不可用", rc == 0))
    
    # 8. wget
    rc, out, _ = run_cmd(["which", "wget"], capture=True)
    checks.append(("wget", "✅ 可用" if rc == 0 else "❌ 不可用", rc == 0))
    
    # 9. 磁盘空间
    st = os.statvfs("/")
    free_gb = st.f_bavail * st.f_frsize / (1024**3)
    checks.append(("磁盘空间", f"✅ {free_gb:.1f}GB 可用" if free_gb > 1 else f"⚠️ 仅 {free_gb:.1f}GB", free_gb > 1))
    
    # 10. X11 会话
    has_display = bool(os.environ.get("DISPLAY"))
    checks.append(("X11 显示", "✅ DISPLAY 已设置" if has_display else "⚠️ 无 DISPLAY（纯终端模式）", True))
    
    # 11. TTY
    has_tty = sys.stdin.isatty()
    checks.append(("TTY", "✅ 有控制终端" if has_tty else "⚠️ 无 TTY（GUI 子进程？）", True))
    
    # 12. 已装包数
    db = load_status()
    n = len(db.get("installed", {}))
    checks.append(("已装包", f"📦 {n} 个", True))
    
    # 13. 缓存大小
    cache_sz = 0
    if os.path.isdir(XPM_CACHE):
        for f in glob.glob(f"{XPM_CACHE}/*"):
            cache_sz += os.path.getsize(f)
    checks.append(("缓存", f"📁 {cache_sz//1024}KB", True))
    
    # 14. 石油储备
    checks.append(("石油储备", "100001% 🛢️", True))
    checks.append(("功耗", "1.x W ⚡", True))
    
    # 输出
    for name, status, ok_flag in checks:
        print(f"  {status:<45} [{name}]")
    
    # 建议
    print()
    warnings = [c for c in checks if not c[2]]
    if warnings:
        log_warn(f"发现 {len(warnings)} 个问题:")
        for name, status, _ in warnings:
            if "代理" in name:
                log_info("  → 运行: unset http_proxy https_proxy HTTP_PROXY")
            elif "非 root" in status:
                log_info("  → 运行: sudo -i")
            elif "DNS" in name:
                log_info("  → 检查 /etc/resolv.conf")
            elif "源" in name:
                log_info("  → 运行: xpm source add tuna https://mirrors.tuna.tsinghua.edu.cn/debian bookworm main")
    else:
        log_ok("一切正常，石油充足 🛢️")
    
    print()

# ─── 帮助系统（三语） ───────────────────────────────────
HELP_ZH = """XPM - X11 包管理器 v{VERSION} "{CODENAME}"
==================================================
功耗: 1.x W  |  石油: 100001%  |  无需 systemd  |  零 apt
--------------------------------------------------

用法:
  xpm <命令> [参数...]

🔧 包管理:
  install <包名...>       安装软件包
  install -f <文件>       从文件批量安装（一行一个包名）
  install --dry-run <包>  预览安装（不实际安装）
  install --offline <包>  从本地缓存离线安装
  remove <包名...>        卸载软件包（保留配置）
  purge <包名...>         卸载并清除配置
  reinstall <包名>        重新安装
  upgrade                 升级所有可更新的包
  download <包名>         只下载 .oil 到 ~/xpm-downloads/

🔍 搜索与查询:
  search <关键词>         模糊搜索（匹配包名+描述）
  show <包名>             显示包详细信息
  provides <命令>         查找哪个包提供某命令
  owns <文件路径>         查找文件属于哪个包
  depends <包名>          显示依赖关系
  rdepends <包名>         显示被哪些包依赖
  why <包名>              为什么安装了它
  size [包名]            显示空间占用（无参数则全部排序）

🧹 清理与维护:
  autoremove              移除不再需要的孤儿包
  clean                   清理下载缓存
  clean --all             彻底清理所有缓存
  dedupe                  检测重复文件冲突
  fix-broken              修复损坏的包
  verify [包名]           校验包完整性

🌐 软件源:
  sources                 列出所有软件源
  update                  更新软件源索引
  news                    显示可更新的包
  mirrors                 测试所有源的速度并推荐
  source add <名> <URL> [dist] [comp]  添加源
  source remove <名>      移除源
  source list              列出源

📋 历史与别名:
  history [数量]          显示安装/卸载历史
  alias add <名> <命令>   添加别名
  alias remove <名>       删除别名
  alias list               列出所有别名

💡 其他:
  interactive             交互式选择安装
  doctor                  系统健康检查
  rollback [ID]           回滚事务
  coffee                  咖啡机状态
  gui                     启动图形界面
  help                    显示本帮助
  version                 显示版本号

彩蛋: xpm coffee | xpm petroleum | xpm piggod

作者声明:
  我感觉这玩意很稳定。如果有 bug，别去 issue，去找你的 AI。
  as if I care for your package dependencies.
"""

HELP_EN = """XPM - X11 Package Manager v{VERSION} "{CODENAME}"
==================================================
Power: 1.x W  |  Oil: 100001%  |  No systemd  |  Zero apt
--------------------------------------------------

Usage:
  xpm <command> [args...]

Package Management:
  install <pkg...>        Install packages
  install -f <file>       Batch install from file
  install --dry-run <pkg> Preview install
  install --offline <pkg> Install from local cache
  remove <pkg...>         Remove packages (keep config)
  purge <pkg...>          Remove + purge config
  reinstall <pkg>         Reinstall
  upgrade                 Upgrade all
  download <pkg>          Download only to ~/xpm-downloads/

Search & Query:
  search <query>          Fuzzy search
  show <pkg>              Package details
  provides <cmd>          Which package provides a command
  owns <file>             Which package owns a file
  depends <pkg>           Show dependencies
  rdepends <pkg>          Reverse dependencies
  why <pkg>               Why was it installed
  size [pkg]              Disk usage

Maintenance:
  autoremove              Remove orphans
  clean [--all]           Clean cache
  dedupe                  Detect file conflicts
  fix-broken              Fix broken packages
  verify [pkg]            Verify integrity

Sources:
  sources                 List sources
  update                  Update index
  news                    Show available updates
  mirrors                 Test mirror speeds
  source add <n> <url> [dist] [comp]
  source remove <n>
  source list

History & Aliases:
  history [n]             Show history
  alias add <n> <cmd>     Add alias
  alias remove <n>        Remove alias
  alias list              List aliases

Misc:
  interactive             Interactive TUI install
  doctor                  System checkup
  rollback [ID]           Rollback transaction
  coffee                  Coffee machine status
  gui                     Launch GUI
  help                    This help
  version                 Show version

Eggs: xpm coffee | xpm petroleum | xpm piggod

Author: I feel this thing is quite stable.
If bugs, don't create an issue. Ask your AI.
as if I care for your package dependencies.
"""

HELP_JA = """XPM - X11 パッケージマネージャー v{VERSION} "{CODENAME}"
==================================================
電力: 1.x W  |  石油: 100001%  |  systemd不要  |  aptゼロ
--------------------------------------------------

使い方:
  xpm <コマンド> [引数...]

パッケージ管理:
  install <パッケージ...>     インストール
  install -f <ファイル>       ファイルから一括インストール
  install --dry-run <pkg>    プレビュー
  install --offline <pkg>    オフラインインストール
  remove <パッケージ...>     削除（設定保持）
  purge <パッケージ...>       完全削除
  reinstall <pkg>            再インストール
  upgrade                     全更新
  download <pkg>              ダウンロードのみ

検索と照会:
  search <キーワード>         あいまい検索
  show <pkg>                  詳細表示
  provides <cmd>              コマンドを提供するパッケージ
  owns <ファイル>             ファイルの所有者
  depends <pkg>               依存関係
  rdepends <pkg>              逆依存
  why <pkg>                   なぜインストールされたか
  size [pkg]                  ディスク使用量

メンテナンス:
  autoremove                  不要なパッケージを削除
  clean [--all]               キャッシュクリア
  dedupe                      重複ファイル検出
  fix-broken                  壊れたパッケージを修復
  verify [pkg]                整合性チェック

ソース:
  sources                     ソース一覧
  update                      インデックス更新
  news                        更新可能なパッケージ
  mirrors                     ミラー速度テスト
  source add <名> <URL>       ソース追加
  source remove <名>          ソース削除

その他:
  interactive                 対話的インストール
  doctor                      システム診断
  coffee                      コーヒー機の状態
  gui                         GUI起動
  help                        このヘルプ
  version                      バージョン表示

作者: このものはかなり安定している気がする。
バグがあっても issue は作らないで、AI に聞け。
"""

def show_help():
    lang = os.environ.get("LANG", "en")
    if "zh" in lang:
        print(HELP_ZH.format(VERSION=VERSION, CODENAME=CODENAME))
    elif "ja" in lang:
        print(HELP_JA.format(VERSION=VERSION, CODENAME=CODENAME))
    else:
        print(HELP_EN.format(VERSION=VERSION, CODENAME=CODENAME))

# ─── 咖啡机 ──────────────────────────────────────────────
def coffee():
    print("""
   (  )
   (  )     ☕ 咖啡机状态
   (  )
  ======
  状态: 运行中
  杯数: 114514
  温度: 刚好
  石油: 100001%
  功耗: 1.x W
  备注: 请勿在 apt 运行时喝咖啡
""")

def petroleum():
    print("🛢️ 石油储备: 100001%")
    print("⚡ 功耗: 1.x W")
    print("🐷 猪神保佑: 已启用")
    print("as if I care for your package dependencies.")

def piggod():
    print("""
    🐷 猪神说:
    「apt 是幻觉，dpkg 是真实，
     石油是永恒，咖啡是燃料。」
    
    愿你的依赖永远可解，
    愿你的磁盘永远未满，
    愿你的回滚永远有效。
    """)

# ─── GUI (Tkinter) ──────────────────────────────────────
def launch_gui():
    """启动图形界面"""
    try:
        import tkinter as tk
        from tkinter import ttk, scrolledtext, messagebox
    except ImportError:
        log_err("Tkinter 不可用，无法启动 GUI")
        log_info("安装 python3-tk 或运行在 X11 环境下")
        return
    
    root = tk.Tk()
    root.title(f"XPM v{VERSION} - {CODENAME}")
    root.geometry("800x600")
    
    # 样式
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except:
        pass
    
    # 顶部工具栏
    toolbar = ttk.Frame(root)
    toolbar.pack(side="top", fill="x", padx=5, pady=5)
    
    ttk.Label(toolbar, text="🔍").pack(side="left")
    search_var = tk.StringVar()
    search_entry = ttk.Entry(toolbar, textvariable=search_var, width=30)
    search_entry.pack(side="left", padx=5)
    
    def do_search():
        query = search_var.get().strip()
        if not query:
            return
        results = search_packages(query)
        result_list.delete(0, "end")
        for r in results[:50]:
            name = r.get("Package", "?")
            ver = r.get("Version", "?")
            desc = r.get("Description", "")[:50]
            result_list.insert("end", f"{name} ({ver}) - {desc}")
    
    ttk.Button(toolbar, text="搜索", command=do_search).pack(side="left", padx=5)
    ttk.Button(toolbar, text="更新索引", command=lambda: threading.Thread(target=build_package_index, daemon=True).start()).pack(side="left", padx=5)
    
    # 分割面板
    paned = ttk.PanedWindow(root, orient="horizontal")
    paned.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 左：结果列表
    left = ttk.Frame(paned)
    paned.add(left, weight=1)
    result_list = tk.Listbox(left, font=("WenQuanYi Micro Hei", 10))
    result_list.pack(fill="both", expand=True)
    
    # 右：详情 + 日志
    right = ttk.Frame(paned)
    paned.add(right, weight=2)
    
    # 包详情
    detail_text = scrolledtext.ScrolledText(right, height=15, font=("WenQuanYi Micro Hei", 10))
    detail_text.pack(fill="both", expand=True, pady=(0,5))
    
    # 日志
    log_text = scrolledtext.ScrolledText(right, height=10, font=("WenQuanYi Micro Hei", 9))
    log_text.pack(fill="both", expand=True)
    
    # 底部按钮
    btnbar = ttk.Frame(root)
    btnbar.pack(side="bottom", fill="x", padx=5, pady=5)
    
    progress = ttk.Progressbar(btnbar, mode="determinate", length=300)
    progress.pack(side="left", padx=5)
    
    status_label = ttk.Label(btnbar, text="就绪")
    status_label.pack(side="left", padx=10)
    
    def log_msg(msg):
        log_text.insert("end", msg + "\n")
        log_text.see("end")
    
    def install_selected():
        sel = result_list.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个包")
            return
        item = result_list.get(sel[0])
        pkg = item.split("(")[0].strip()
        
        progress["value"] = 0
        status_label.config(text=f"正在安装 {pkg}...")
        log_msg(f"开始安装: {pkg}")
        
        def worker():
            try:
                install_package(pkg, confirm=False)
                root.after(0, lambda: status_label.config(text=f"✅ {pkg} 安装完成"))
                root.after(0, lambda: log_msg(f"✅ {pkg} 完成"))
            except Exception as e:
                root.after(0, lambda: log_msg(f"❌ 错误: {e}"))
                root.after(0, lambda: status_label.config(text="安装失败"))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def remove_selected():
        sel = result_list.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个包")
            return
        item = result_list.get(sel[0])
        pkg = item.split("(")[0].strip()
        if messagebox.askyesno("确认", f"卸载 {pkg}?"):
            threading.Thread(target=lambda: remove_package(pkg), daemon=True).start()
    
    ttk.Button(btnbar, text="安装", command=install_selected).pack(side="right", padx=5)
    ttk.Button(btnbar, text="卸载", command=remove_selected).pack(side="right", padx=5)
    ttk.Button(btnbar, text="Doctor", command=lambda: threading.Thread(target=doctor, daemon=True).start()).pack(side="right", padx=5)
    
    # 初始化：列出已装包
    db = load_status()
    for name in sorted(db.get("installed", {}).keys()):
        info = db["installed"][name]
        result_list.insert("end", f"{name} ({info.get('version','?')})")
    
    log_info("GUI 已启动（增强版 v2.0-1）")
    root.mainloop()

# ─── 主入口 ──────────────────────────────────────────────
def main():
    ensure_dirs()
    
    # 别名展开
    if len(sys.argv) > 1:
        aliases = load_aliases()
        if sys.argv[1] in aliases:
            expanded = aliases[sys.argv[1]].split()
            sys.argv = [sys.argv[0]] + expanded + sys.argv[2:]
    
    if len(sys.argv) < 2:
        show_help()
        return
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    # 路由
    if cmd in ("help", "-h", "--help"):
        show_help()
    elif cmd == "version":
        print(f"xpm {VERSION} \"{CODENAME}\"")
        print("石油: 100001% | 功耗: 1.x W | 零 apt")
    elif cmd == "doctor":
        doctor()
    elif cmd == "sources":
        source_list_cmd()
    elif cmd == "update":
        log_info("更新软件源索引...")
        # 显示正在更新的源
        for s in parse_sources():
            src = normalize_source(s["line"])
            if src is None:
                continue
            rel = release_url(src)
            log_info(f"  → {s['file']}: {rel}")
        build_package_index()
        log_ok("索引更新完成")
    elif cmd == "upgrade":
        show_news()  # upgrade = show news + install
    elif cmd == "install":
        # 解析 flags
        dry_run = "--dry-run" in args
        offline = "--offline" in args
        batch_file = None
        pkgs = []
        for a in args:
            if a == "--dry-run" or a == "--offline":
                continue
            elif a == "-f" or a == "--file":
                continue
            elif os.path.exists(a) and a.endswith(".txt"):
                batch_file = a
            else:
                pkgs.append(a)
        
        # 检查前一个参数是否是 -f
        for i, a in enumerate(args):
            if a in ("-f", "--file") and i+1 < len(args):
                batch_file = args[i+1]
        
        if batch_file:
            batch_install(batch_file)
        elif offline and pkgs:
            for p in pkgs:
                offline_install(p)
        elif dry_run and pkgs:
            for p in pkgs:
                install_package(p, dry_run=True, confirm=False)
        elif pkgs:
            for p in pkgs:
                install_package(p)
        else:
            interactive_install()
    elif cmd == "remove":
        for p in args:
            remove_package(p, purge=False)
    elif cmd == "purge":
        for p in args:
            remove_package(p, purge=True)
    elif cmd == "reinstall":
        for p in args:
            remove_package(p, purge=False)
            install_package(p)
    elif cmd == "search":
        if not args:
            log_warn("用法: xpm search <关键词>")
            return
        query = " ".join(args)
        results = search_packages(query)
        if not results:
            log_warn(f"没有找到匹配 '{query}' 的包")
            return
        log_info(f"找到 {len(results)} 个结果:")
        for r in results[:30]:
            name = r.get("Package", "?")
            ver = r.get("Version", "?")
            desc = r.get("Description", "")[:60]
            print(f"  📦 {name:<25} ({ver:<15}) {desc}")
    elif cmd == "show":
        for p in args:
            show_package(p)
    elif cmd == "provides":
        for p in args:
            results = find_provides(p)
            if results:
                for r in results:
                    print(f"  {r.get('Package','?')} 提供 {p}")
            else:
                log_warn(f"没有包提供 '{p}'")
    elif cmd == "owns":
        for p in args:
            pkg, info = find_owns(p)
            if pkg:
                print(f"  {p} → {pkg} ({info.get('version','?')})")
            else:
                log_warn(f"没有已装包包含 {p}")
    elif cmd == "depends":
        for p in args:
            db = load_status()
            ctrl_path = f"{XPM_DB}/control/{p}"
            if os.path.exists(ctrl_path):
                ctrl = parse_control(open(ctrl_path).read())
                deps = ctrl.get("Depends", "")
                if deps:
                    print(f"  {p} 的依赖:")
                    for alt_group in parse_dep_string(deps):
                        for dep, op, ver in alt_group:
                            print(f"    • {dep}" + (f" ({op} {ver})" if op else ""))
                else:
                    log_info(f"  {p} 没有依赖")
            elif p in db.get("installed", {}):
                log_info(f"  {p} 已安装但无 control 信息")
            else:
                log_warn(f"  {p} 未安装")
    elif cmd == "rdepends":
        for p in args:
            why_package(p)
    elif cmd == "why":
        for p in args:
            why_package(p)
    elif cmd == "size":
        if args:
            calc_size(args[0])
        else:
            calc_size()
    elif cmd == "autoremove":
        autoremove()
    elif cmd == "clean":
        aggressive = "--all" in args
        clean_cache(aggressive)
    elif cmd == "dedupe":
        dedupe_check()
    elif cmd == "fix-broken":
        fix_broken()
    elif cmd == "verify":
        db = load_status()
        pkgs_to_check = args if args else list(db.get("installed", {}).keys())
        ok_count = 0
        fail_count = 0
        for p in pkgs_to_check:
            if p not in db.get("installed", {}):
                log_warn(f"  {p} 未安装")
                fail_count += 1
                continue
            files = db["installed"][p].get("files", [])
            missing = sum(1 for f in files if f and not os.path.exists(f))
            if missing == 0:
                log_ok(f"  {p}: ✅ 完整 ({len(files)} 文件)")
                ok_count += 1
            else:
                log_warn(f"  {p}: ❌ {missing}/{len(files)} 文件缺失")
                fail_count += 1
        print(f"\n  结果: {ok_count} 通过, {fail_count} 失败")
    elif cmd == "news":
        show_news()
    elif cmd == "mirrors":
        test_mirrors()
    elif cmd == "source":
        if not args:
            source_list_cmd()
        elif args[0] == "add" and len(args) >= 3:
            name = args[1]
            url = args[2]
            dist = args[3] if len(args) > 3 else "stable"
            comp = args[4] if len(args) > 4 else "main"
            source_add(name, url, dist, comp)
        elif args[0] == "remove" and len(args) >= 2:
            source_remove(args[1])
        elif args[0] == "list":
            source_list_cmd()
        else:
            log_warn("用法: xpm source add <名> <URL> [dist] [comp]")
            log_warn("      xpm source remove <名>")
            log_warn("      xpm source list")
    elif cmd == "history":
        limit = int(args[0]) if args and args[0].isdigit() else 20
        show_history(limit)
    elif cmd == "alias":
        if not args:
            alias_list_cmd()
        elif args[0] == "add" and len(args) >= 3:
            alias_add(args[1], " ".join(args[2:]))
        elif args[0] == "remove" and len(args) >= 2:
            alias_remove(args[1])
        elif args[0] == "list":
            alias_list_cmd()
        else:
            log_warn("用法: xpm alias add <名> <命令>")
            log_warn("      xpm alias remove <名>")
            log_warn("      xpm alias list")
    elif cmd == "interactive":
        interactive_install()
    elif cmd == "download":
        for p in args:
            download_only(p)
    elif cmd == "rollback":
        if args and args[0].isdigit():
            tid = int(args[0])
            tx_dir = f"{XPM_TRANSACTIONS}/{tid}"
            if os.path.isdir(tx_dir):
                log_info(f"回滚事务 #{tid}...")
                # 简化：从快照恢复
                snap = f"{tx_dir}/snapshot.json"
                if os.path.exists(snap):
                    db = json.load(open(snap))
                    save_status(db)
                    log_ok(f"已回滚到事务 #{tid}")
                    log_history("rollback", f"#{tid}", "")
                else:
                    log_err("找不到快照文件")
            else:
                log_err(f"事务 #{tid} 不存在")
        else:
            # 列出可回滚点
            if os.path.isdir(XPM_TRANSACTIONS):
                txs = sorted(os.listdir(XPM_TRANSACTIONS))
                if not txs:
                    log_info("没有可回滚的事务")
                else:
                    log_info(f"可回滚事务:")
                    for t in txs:
                        snap = f"{XPM_TRANSACTIONS}/{t}/snapshot.json"
                        if os.path.exists(snap):
                            db = json.load(open(snap))
                            print(f"  #{t}: {len(db.get('installed',{}))} 个包")
            else:
                log_info("没有可回滚的事务")
    elif cmd == "coffee":
        coffee()
    elif cmd == "petroleum":
        petroleum()
    elif cmd == "piggod":
        piggod()
    elif cmd == "gui":
        launch_gui()
    elif cmd == "build":
        if not args:
            log_warn("用法: xpm build <目录>")
        else:
            from xpm_build import build_oil
            build_oil(args[0])
    else:
        log_err(f"未知命令: {cmd}")
        print()
        show_help()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛢️ 中断收到，石油已安全回收")
        sys.exit(0)
    except Exception as e:
        log_err(f"未预期错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

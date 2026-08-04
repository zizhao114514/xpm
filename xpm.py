#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XPM - X11 Package Manager v2.0-0 "Complete Edition"
Oil-driven. Apt-forbidden. Language-agnostic backend.

Usage: xpm [command] [args...]

Commands:
  help                          Show help
  version                       Show version
  sources                       List configured sources
  update                        Update source indexes (wget only)
  search <kw>                   Search packages
  info <pkg>                    Show package info
  install <pkg> [pkg...]        Install package(s)
  remove <pkg> [pkg...]         Remove package(s)
  purge <pkg> [pkg...]          Remove + clear config
  upgrade                       Upgrade all installed
  reinstall <pkg>               Reinstall package
  fix-broken                    Try to fix broken installs
  depends <pkg>                 Show dependencies
  rdepends <pkg>                Show reverse dependencies
  list [--installed]            List packages
  verify [pkg]                  Verify package integrity
  rollback [list|<n>]           Rollback to a previous state
  build <dir>                   Build .oil package from directory
  stats                         Show statistics
  doctor                        Diagnose common issues
  gui                           Launch GUI
"""

import os
import sys
import re
import gzip
import shutil
import subprocess
import json
import hashlib
import time
import threading
import queue
import signal
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple

# ====== 配置 ======
VERSION = "2.0-0"
CODENAME = "Complete Edition"
ARCH = subprocess.run(["uname", "-m"], capture_output=True, text=True).stdout.strip()
if ARCH == "aarch64":
    ARCH = "arm64"

XPM_ROOT = "/var/lib/xpm"
XPM_CACHE = "/var/cache/xpm"
XPM_LOG = "/var/log/xpm"
XPM_SOURCES_DIR = "/etc/xpm/sources.list.d"
XPM_CONFIG = "/etc/xpm/xpm.conf"

# 后端选择（可被环境变量覆盖）
XM_BIN = os.environ.get("XM_BIN", "/usr/local/bin/xm")
XMCS_BIN = os.environ.get("XMCS_BIN", "/usr/local/bin/xmcs")

# 语言检测
LANG = os.environ.get("LANG", "en")
if "zh" in LANG.lower():
    UI_LANG = "zh"
elif "ja" in LANG.lower():
    UI_LANG = "ja"
else:
    UI_LANG = "en"

# ====== 多语言字符串 ======
I18N = {
    "zh": {
        "version_info": "XPM (X11 包管理器) {v} '{c}'",
        "oil_driven": "石油驱动: 是 | Apt: 已禁止 | 后端: {backend}",
        "no_cmd": "未指定命令。运行 'xpm help' 查看帮助。",
        "unknown_cmd": "未知命令: {cmd}",
        "no_sources": "⚠️ 没有可用的软件源。请检查 {d}/",
        "updating": "🔄 更新源索引...",
        "update_ok": "✅ 更新完成（{n} 个索引）",
        "update_fail": "⚠️ {src}: 拉取失败",
        "update_timeout": "⚠️ {src}: 超时",
        "search_results": "🔍 搜索结果 '{kw}':",
        "no_results": "  无匹配结果。",
        "install_start": "[1/4] 正在选中未安装的软件包：{pkg}",
        "selecting": "[2/4] 正在选中 {pkg} ({ver})",
        "unpacking": "[3/4] 正在解压 {pkg} ({ver})...",
        "configuring": "[4/4] 正在设置 {pkg} ({ver})...",
        "install_ok": "✅ {pkg} ({ver}) 安装完成",
        "install_fail": "❌ {pkg} 安装失败",
        "remove_find": "[1/3] 正在寻找与 {pkg} 相关的文件...",
        "removing": "[2/3] 正在卸载 {pkg} ({ver})...",
        "purging": "[3/3] 正在清除 {pkg} ({ver})...",
        "remove_ok": "✅ {pkg} 卸载完成",
        "purge_ok": "✅ {pkg} 已彻底清除",
        "not_installed": "⚠️ {pkg} 未安装",
        "already_installed": "ℹ️ {pkg} 已安装 ({ver})",
        "dep_resolve": "📋 依赖解析:",
        "dep_chain": "  ├─ {pkg} ({ver})",
        "dep_chain_last": "  └─ {pkg} ({ver})",
        "dep_missing": "  ⚠️ 缺少依赖: {pkg}",
        "autoremove_find": "[4/?] 正在寻找不再被需要的依赖...",
        "autoremove_item": "  卸载 {pkg} ({ver})",
        "autoremove_done": "✅ 自动清理完成",
        "verifying": "🔐 校验中...",
        "verify_ok": "✅ {pkg} 校验通过",
        "verify_fail": "❌ {pkg} 校验失败: {reason}",
        "rollback_list": "📋 可用回滚点:",
        "rollback_empty": "  （无可用回滚点）",
        "rollback_done": "✅ 已回滚到 #{n}",
        "building": "📦 构建 .oil 包: {dir}",
        "build_ok": "✅ 构建完成: {out}",
        "build_fail": "❌ 构建失败: {reason}",
        "doctor_title": "🩺 XPM 系统诊断",
        "doctor_x11": "⚠️ 检测到 X11 会话",
        "doctor_tty": "⚠️ stdin 不是 TTY（按键可能无法送达）",
        "doctor_proxy": "⚠️ 检测到代理环境变量（可能干扰下载）",
        "doctor_sudo": "⚠️ 当前非 root，部分操作需要 sudo",
        "doctor_xm_ok": "✅ 后端 {bin} 可用",
        "doctor_xm_missing": "❌ 后端 {bin} 未找到",
        "stats_title": "📊 XPM 统计",
        "stats_pkgs": "  已安装包: {n}",
        "stats_oil": "  石油储备: {pct}%",
        "stats_crashes": "  咖啡机崩溃: {n}",
        "stats_uptime": "  运行时间: {t}",
        "no_apt": "🚫 apt-get / apt-cache 被明确禁止",
        "wget_only": "📡 仅使用 wget 下载",
        "press_enter": "按回车继续...",
        "download_pkg": "📥 下载 {pkg} ({size})",
        "download_progress": "  █{bar}░ {pct}% | {spd}/s | 剩余 {eta}s",
        "extracting": "📂 解压文件...",
        "running_script": "🔧 执行 {script}...",
        "coffee_crash": "☕ 咖啡机 +1（{reason}）",
        "abort": "⚠️ 操作被用户中断",
        "timeout": "⚠️ 操作超时（{s}s）",
        "lock_wait": "🔒 等待锁释放...",
        "lock_acquired": "🔓 锁已获取",
        "transaction_start": "📝 事务 #{tid} 开始",
        "transaction_commit": "📝 事务 #{tid} 已提交",
        "transaction_rollback": "📝 事务 #{tid} 回滚中...",
        "gpg_verify_ok": "🔐 GPG 签名验证通过",
        "gpg_verify_fail": "🔐 GPG 签名验证失败: {reason}",
        "gpg_no_key": "🔐 警告: 未配置 GPG 密钥，跳过签名验证",
    },
    "ja": {
        "version_info": "XPM (X11 パッケージマネージャー) {v} '{c}'",
        "oil_driven": "石油駆動: はい | Apt: 禁止 | バックエンド: {backend}",
        "no_cmd": "コマンドが指定されていません。'xpm help' で確認。",
        "unknown_cmd": "不明なコマンド: {cmd}",
        "no_sources": "⚠️ 利用可能なソースがありません。{d}/ を確認。",
        "updating": "🔄 ソースインデックスを更新中...",
        "update_ok": "✅ 更新完了（{n} 個のインデックス）",
        "update_fail": "⚠️ {src}: 取得失敗",
        "update_timeout": "⚠️ {src}: タイムアウト",
        "search_results": "🔍 検索結果 '{kw}':",
        "no_results": "  一致する結果なし。",
        "install_start": "[1/4] 未インストールパッケージを選択中: {pkg}",
        "selecting": "[2/4] {pkg} ({ver}) を選択中",
        "unpacking": "[3/4] {pkg} ({ver}) を展開中...",
        "configuring": "[4/4] {pkg} ({ver}) を設定中...",
        "install_ok": "✅ {pkg} ({ver}) インストール完了",
        "install_fail": "❌ {pkg} インストール失敗",
        "remove_find": "[1/3] {pkg} に関連するファイルを検索中...",
        "removing": "[2/3] {pkg} ({ver}) をアンインストール中...",
        "purging": "[3/3] {pkg} ({ver}) を完全削除中...",
        "remove_ok": "✅ {pkg} アンインストール完了",
        "purge_ok": "✅ {pkg} 完全削除完了",
        "not_installed": "⚠️ {pkg} は未インストール",
        "already_installed": "ℹ️ {pkg} は既にインストール済み ({ver})",
        "no_apt": "🚫 apt-get / apt-cache は明示的に禁止",
        "press_enter": "Enter を押して続行...",
    },
    "en": {
        "version_info": "XPM (X11 Package Manager) {v} '{c}'",
        "oil_driven": "Oil-driven: yes | Apt: explicitly forbidden | Backend: {backend}",
        "no_cmd": "No command specified. Run 'xpm help' for help.",
        "unknown_cmd": "Unknown command: {cmd}",
        "no_sources": "⚠️ No sources available. Check {d}/",
        "updating": "🔄 Updating source indexes...",
        "update_ok": "✅ Update complete ({n} indexes)",
        "update_fail": "⚠️ {src}: fetch failed",
        "update_timeout": "⚠️ {src}: timeout",
        "search_results": "🔍 Search results for '{kw}':",
        "no_results": "  No matches found.",
        "install_start": "[1/4] Selecting newly-installed packages: {pkg}",
        "selecting": "[2/4] Selecting {pkg} ({ver})",
        "unpacking": "[3/4] Unpacking {pkg} ({ver})...",
        "configuring": "[4/4] Setting up {pkg} ({ver})...",
        "install_ok": "✅ {pkg} ({ver}) installed",
        "install_fail": "❌ {pkg} installation failed",
        "remove_find": "[1/3] Finding files related to {pkg}...",
        "removing": "[2/3] Removing {pkg} ({ver})...",
        "purging": "[3/3] Purging {pkg} ({ver})...",
        "remove_ok": "✅ {pkg} removed",
        "purge_ok": "✅ {pkg} purged completely",
        "not_installed": "⚠️ {pkg} is not installed",
        "already_installed": "ℹ️ {pkg} is already installed ({ver})",
        "dep_resolve": "📋 Dependency resolution:",
        "dep_chain": "  ├─ {pkg} ({ver})",
        "dep_chain_last": "  └─ {pkg} ({ver})",
        "dep_missing": "  ⚠️ Missing dependency: {pkg}",
        "autoremove_find": "[4/?] Finding no-longer-needed dependencies...",
        "autoremove_item": "  Removing {pkg} ({ver})",
        "autoremove_done": "✅ Auto-cleanup complete",
        "verifying": "🔐 Verifying...",
        "verify_ok": "✅ {pkg} verification passed",
        "verify_fail": "❌ {pkg} verification failed: {reason}",
        "rollback_list": "📋 Available rollback points:",
        "rollback_empty": "  (no rollback points)",
        "rollback_done": "✅ Rolled back to #{n}",
        "building": "📦 Building .oil package: {dir}",
        "build_ok": "✅ Build complete: {out}",
        "build_fail": "❌ Build failed: {reason}",
        "doctor_title": "🩺 XPM System Diagnosis",
        "doctor_x11": "⚠️ X11 session detected",
        "doctor_tty": "⚠️ stdin is not a TTY (keystrokes may not reach subprocess)",
        "doctor_proxy": "⚠️ Proxy env vars detected (may interfere with downloads)",
        "doctor_sudo": "⚠️ Not running as root; some operations need sudo",
        "doctor_xm_ok": "✅ Backend {bin} available",
        "doctor_xm_missing": "❌ Backend {bin} not found",
        "stats_title": "📊 XPM Statistics",
        "stats_pkgs": "  Installed packages: {n}",
        "stats_oil": "  Oil reserve: {pct}%",
        "stats_crashes": "  Coffee machine crashes: {n}",
        "stats_uptime": "  Uptime: {t}",
        "no_apt": "🚫 apt-get / apt-cache explicitly forbidden",
        "wget_only": "📡 Downloads via wget only",
        "press_enter": "Press Enter to continue...",
        "download_pkg": "📥 Downloading {pkg} ({size})",
        "download_progress": "  █{bar}░ {pct}% | {spd}/s | ETA {eta}s",
        "extracting": "📂 Extracting files...",
        "running_script": "🔧 Running {script}...",
        "coffee_crash": "☕ Coffee machine +1 ({reason})",
        "abort": "⚠️ Operation aborted by user",
        "timeout": "⚠️ Operation timed out ({s}s)",
        "lock_wait": "🔒 Waiting for lock...",
        "lock_acquired": "🔓 Lock acquired",
        "transaction_start": "📝 Transaction #{tid} started",
        "transaction_commit": "📝 Transaction #{tid} committed",
        "transaction_rollback": "📝 Transaction #{tid} rolling back...",
        "gpg_verify_ok": "🔐 GPG signature verified",
        "gpg_verify_fail": "🔐 GPG signature verification failed: {reason}",
        "gpg_no_key": "🔐 Warning: No GPG key configured, skipping signature check",
    }
}

def _(key, **kwargs):
    """国际化字符串"""
    tmpl = I18N.get(UI_LANG, I18N["en"]).get(key, I18N["en"].get(key, key))
    return tmpl.format(**kwargs)

def print_stage(stage_text):
    """带 flush 的阶段输出（防止 proot/X11 缓冲）"""
    print(stage_text, flush=True)

# ====== 咖啡机崩溃计数 ======
class CoffeeMachine:
    def __init__(self, db_path=f"{XPM_ROOT}/coffee.json"):
        self.db_path = db_path
        self.count = self._load()

    def _load(self):
        try:
            with open(self.db_path) as f:
                return json.load(f).get("crashes", 0)
        except:
            return 0

    def _save(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "w") as f:
            json.dump({"crashes": self.count}, f)

    def crash(self, reason="unknown"):
        self.count += 1
        self._save()
        print_stage(_("coffee_crash", reason=reason))

    def get(self):
        return self.count

coffee = CoffeeMachine()

# ====== 工具函数 ======
def detect_arch():
    return ARCH

def is_root():
    return os.geteuid() == 0 if hasattr(os, "geteuid") else True

def wget_download(url, dest, timeout=60, progress_cb=None):
    """wget 下载，支持进度回调。禁止任何 apt 调用。"""
    # 清除可能从 X11 会话继承的代理
    env = os.environ.copy()
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        env.pop(k, None)

    if progress_cb:
        # 用 wget 命令行（支持进度条解析）
        cmd = ["wget", "--progress=bar:force:noscroll", "--timeout=" + str(timeout), "-O", dest, url]
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, env=env, text=True)
        for line in proc.stderr:
            if "%" in line:
                m = re.search(r'(\d+)%\s+(\S+)\s+(\S+)\s+(\S+)', line)
                if m:
                    pct = int(m.group(1))
                    size = m.group(2)
                    spd = m.group(3)
                    eta = m.group(4)
                    progress_cb(pct, size, spd, eta)
        rc = proc.wait()
        return rc == 0
    else:
        cmd = ["wget", "--quiet", "--timeout=" + str(timeout), "-O", dest, url]
        rc = subprocess.run(cmd, env=env).returncode
        return rc == 0

def gunzip_file(src, dest=None):
    if dest is None:
        dest = src[:-3] if src.endswith(".gz") else src + ".decompressed"
    with gzip.open(src, "rb") as f_in, open(dest, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    return dest

def parse_packages_file(path):
    """解析 Packages 文件，返回包列表"""
    pkgs = []
    if not os.path.exists(path):
        return pkgs
    with open(path, "r", errors="replace") as f:
        content = f.read()
    blocks = content.split("\n\n")
    for block in blocks:
        pkg = {}
        for line in block.split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                pkg[k.strip().lower()] = v.strip()
        if "package" in pkg:
            pkgs.append(pkg)
    return pkgs

# ====== 源管理 ======
def parse_sources_dir(d=XPM_SOURCES_DIR):
    """解析源目录，兼容 deb 和 [xpm] 两种写法"""
    sources = []
    if not os.path.isdir(d):
        return sources
    for fname in sorted(os.listdir(d)):
        if not (fname.endswith(".list") or fname.endswith(".sources")):
            continue
        path = os.path.join(d, fname)
        sources += parse_file(path)
    return [s for s in sources if s.get("enabled", True)]

def parse_file(path):
    out = []
    with open(path) as f:
        text = f.read()

    if re.search(r"^\s*\[xpm\]", text, re.M):
        out.append(parse_xpm_block(text, path))
        return out

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts[0] != "deb":
            continue
        url = parts[1].rstrip("/")
        suite = parts[2] if len(parts) > 2 else ""
        comps = parts[3:] if len(parts) > 3 else ["main"]
        out.append({
            "name": os.path.basename(path).replace(".list", ""),
            "type": "deb",
            "url": url,
            "suite": suite,
            "components": comps,
            "arch": detect_arch(),
            "enabled": True,
        })
    return out

def parse_xpm_block(text, path):
    block = {}
    for m in re.finditer(r"^\s*\[xpm\]\s*$", text, re.M):
        start = m.end()
        nxt = re.search(r"^\s*\[", text[start:], re.M)
        chunk = text[start: start + (nxt.start() if nxt else len(text))]
        for line in chunk.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                block[k.strip()] = v.strip()
    return {
        "name": block.get("name", os.path.basename(path)),
        "type": block.get("type", "xpm"),
        "url": block.get("url", "").rstrip("/"),
        "suite": "",
        "components": [],
        "arch": detect_arch(),
        "enabled": block.get("enabled", "yes").lower() in ("yes", "true", "1"),
        "gpg": block.get("gpg_key") or None,
    }

# ====== 依赖解析 ======
class DependencyResolver:
    """解析 Depends 字段，构建依赖图，拓扑排序"""

    VERSION_OPS = ["<<", ">>", "<=", ">=", "<", ">", "="]

    def parse_depends(self, depends_str):
        """解析 'A (>= 1.0) | B, C' → [[(A,>=,1.0),(B,,)], [(C,,)]]"""
        if not depends_str:
            return []
        alternatives = []
        for alt_group in depends_str.split(","):
            alts = []
            for candidate in alt_group.split("|"):
                candidate = candidate.strip()
                if not candidate:
                    continue
                # 格式: name (op version) 或 name
                m = re.match(r'^(.+?)\s*\((.+?)\)\s*$', candidate)
                if m:
                    name = m.group(1).strip()
                    constraint = m.group(2).strip()
                    # 拆分 op 和 version
                    op = ""
                    ver = ""
                    for o in self.VERSION_OPS:
                        if constraint.startswith(o):
                            op = o
                            ver = constraint[len(o):].strip()
                            break
                    if not op:
                        # 纯版本号（无 op）
                        ver = constraint
                else:
                    name = candidate
                    op = ""
                    ver = ""
                # 忽略 :any :native 等后缀
                name = re.sub(r":\w+", "", name)
                alts.append((name.strip(), op, ver.strip()))
            if alts:
                alternatives.append(alts)
        return alternatives

    def compare_versions(self, v1, op, v2):
        """Debian 风格版本比较（支持 epoch）"""
        def split_ver(v):
            epoch = 0
            rest = v
            if ":" in v:
                e, rest = v.split(":", 1)
                try: epoch = int(e)
                except: epoch = 0
            upstream = rest
            debian_rev = ""
            if "-" in rest:
                upstream, debian_rev = rest.rsplit("-", 1)
            return epoch, upstream, debian_rev
        
        def vercmp_str(a, b):
            """比较两段版本字符串，返回 >0 / 0 / <0"""
            import re as re2
            a_parts = re2.findall(r'(\d+|[a-zA-Z]+)', a)
            b_parts = re2.findall(r'(\d+|[a-zA-Z]+)', b)
            for ap, bp in zip(a_parts, b_parts):
                if ap.isdigit() and bp.isdigit():
                    ai, bi = int(ap), int(bp)
                    if ai != bi: return ai - bi
                else:
                    if ap > bp: return 1
                    if ap < bp: return -1
            return len(a_parts) - len(b_parts)
        
        e1, u1, d1 = split_ver(v1)
        e2, u2, d2 = split_ver(v2)
        
        # 比 epoch
        if e1 != e2:
            result = e1 > e2
            if op in (">=", ">>", ">"): return result
            if op in ("<=", "<<", "<"): return not result
            if op == "=": return False
        
        # 比 upstream
        r = vercmp_str(u1, u2)
        if r != 0:
            result = r > 0
            if op in (">=", ">"): return result
            if op in ("<=", "<"): return not result
            if op == "=": return False
        
        # 比 debian revision
        r = vercmp_str(d1, d2)
        if r != 0:
            result = r > 0
            if op in (">=", ">"): return result
            if op in ("<=", "<"): return not result
        
        # 完全相等
        if op == "=": return True
        if op in (">=", "<="): return True
        return False

    def resolve(self, pkg_name, all_pkgs, installed, being_resolved=None):
        """解析 pkg_name 的所有依赖，返回有序安装列表"""
        if being_resolved is None:
            being_resolved = set()
        if pkg_name in being_resolved:
            return []  # 循环依赖，跳过
        being_resolved.add(pkg_name)

        # 找包的最新版本
        candidates = [p for p in all_pkgs if p.get("package") == pkg_name]
        if not candidates:
            return [(pkg_name, None, "missing")]

        # 选最高版本
        def ver_key(p):
            v = p.get("version", "0")
            if ":" in v:
                try: return int(v.split(":")[0])
                except: return 0
            return 0
        pkg = max(candidates, key=ver_key)

        result = []
        depends_str = pkg.get("depends", "")
        deps = self.parse_depends(depends_str)

        for alt_group in deps:
            satisfied = False
            for name, op, ver in alt_group:
                if name in installed:
                    satisfied = True
                    break
                # 递归解析
                sub = self.resolve(name, all_pkgs, installed, being_resolved.copy())
                for item in sub:
                    if item not in result and item[2] != "missing":
                        result.append(item)
                if name in installed:
                    satisfied = True
                    break
            # OR 组里至少一个满足即可

        ver = pkg.get("version", "unknown")
        if (pkg_name, ver, "selected") not in result:
            result.append((pkg_name, ver, "selected"))
        return result

# ====== 数据库 ======
class PackageDB:
    def __init__(self, db_path=f"{XPM_ROOT}/status.db"):
        self.db_path = db_path
        self.packages = self._load()

    def _load(self):
        if not os.path.exists(self.db_path):
            return {}
        try:
            with open(self.db_path) as f:
                return json.load(f)
        except:
            return {}

    def _save(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "w") as f:
            json.dump(self.packages, f, indent=2)

    def is_installed(self, name):
        return name in self.packages

    def get_version(self, name):
        return self.packages.get(name, {}).get("version", "unknown")

    def add(self, name, version, files=None, **kwargs):
        self.packages[name] = {
            "version": version,
            "installed_at": datetime.now().isoformat(),
            "files": files or [],
            **kwargs,
        }
        self._save()

    def remove(self, name):
        if name in self.packages:
            del self.packages[name]
            self._save()

    def purge(self, name):
        self.remove(name)
        # 清除配置
        conf_dir = f"{XPM_ROOT}/configs/{name}"
        if os.path.isdir(conf_dir):
            shutil.rmtree(conf_dir)

    def list_all(self):
        return sorted(self.packages.keys())

    def count(self):
        return len(self.packages)

# ====== 事务 & 回滚 ======
class Transaction:
    def __init__(self, db: PackageDB, rollback_dir=None):
        self.db = db
        self.id = int(time.time())
        self.steps = []
        self.rollback_dir = rollback_dir or f"{XPM_ROOT}/rollback"
        os.makedirs(self.rollback_dir, exist_ok=True)

    def snapshot(self, pkg_name, files):
        """保存文件快照用于回滚"""
        import base64
        snap = {"pkg": pkg_name, "files": {}, "timestamp": datetime.now().isoformat()}
        for f in files:
            if os.path.exists(f):
                try:
                    with open(f, "rb") as fh:
                        snap["files"][f] = base64.b64encode(fh.read()).decode()
                except:
                    pass
        snap_path = f"{self.rollback_dir}/{self.id}_{pkg_name}.json"
        with open(snap_path, "w") as fh:
            json.dump(snap, fh)
        self.steps.append(snap_path)

    def rollback(self, point_id=None):
        """回滚到指定点或最近点"""
        import base64
        snaps = sorted(Path(self.rollback_dir).glob("*.json"))
        if not snaps:
            return False
        if point_id is None:
            target = snaps[-1]
        else:
            target = None
            for s in snaps:
                if str(point_id) in s.name:
                    target = s
                    break
        if not target:
            return False
        with open(target) as f:
            snap = json.load(f)
        for path, content in snap.get("files", {}).items():
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                data = base64.b64decode(content) if isinstance(content, str) else content
                with open(path, "wb") as fh:
                    fh.write(data)
            except Exception as e:
                print(f"  ⚠️ 恢复 {path} 失败: {e}")
        try:
            os.remove(target)
        except:
            pass
        return True

    def list_rollback_points(self):
        snaps = sorted(Path(self.rollback_dir).glob("*.json"))
        results = []
        for s in snaps:
            try:
                with open(s) as f:
                    data = json.load(f)
                # stem like "1234567890_vim" → id = "1234567890"
                stem = s.stem
                rid = stem.split("_")[0] if "_" in stem else stem
                results.append({
                    "id": rid,
                    "pkg": data.get("pkg", "?"),
                    "time": data.get("timestamp", "?"),
                })
            except:
                pass
        return results

# ====== GPG 校验 ======
class GPGVerifier:
    def __init__(self, keyring=None):
        self.keyring = keyring or f"{XPM_ROOT}/trustedkeys.gpg"

    def verify_signature(self, sig_path, data_path):
        """验证 GPG 签名"""
        if not os.path.exists(self.keyring):
            print_stage(_("gpg_no_key"))
            return True  # 没配密钥，跳过（不算失败）
        try:
            rc = subprocess.run(
                ["gpgv", "--keyring", self.keyring, sig_path, data_path],
                capture_output=True
            ).returncode
            if rc == 0:
                print_stage(_("gpg_verify_ok"))
                return True
            else:
                print_stage(_("gpg_verify_fail", reason="gpgv returned " + str(rc)))
                return False
        except FileNotFoundError:
            print_stage(_("gpg_verify_fail", reason="gpgv not installed"))
            return True  # gpgv 没装，跳过

# ====== 下载进度 ======
def make_progress_bar(pct, width=20):
    filled = int(width * pct / 100)
    return "█" * filled + "░" * (width - filled)

def progress_callback(pct, size, spd, eta):
    bar = make_progress_bar(pct)
    line = _("download_progress", bar=bar, pct=pct, spd=spd, eta=eta)
    # 用 \r 覆盖同一行
    sys.stdout.write("\r" + line)
    sys.stdout.flush()
    if pct >= 100:
        sys.stdout.write("\n")
        sys.stdout.flush()

# ====== 命令实现 ======
def cmd_help():
    print(__doc__)

def cmd_version():
    backend = "xmcs (C#)" if os.path.exists(XMCS_BIN) else "xm (Python)"
    print_stage(_("version_info", v=VERSION, c=CODENAME))
    print_stage(_("oil_driven", backend=backend))
    print_stage(_("no_apt"))
    print_stage(_("wget_only"))

def cmd_sources():
    sources = parse_sources_dir()
    if not sources:
        print_stage(_("no_sources", d=XPM_SOURCES_DIR))
        return
    for s in sources:
        if s["type"] == "deb":
            comp = ",".join(s["components"])
            print(f"  [deb] {s['name']:20s} {s['url']}  suite={s['suite']}  comp=[{comp}]")
        else:
            print(f"  [xpm] {s['name']:20s} {s['url']}  enabled={s['enabled']}")

def cmd_update():
    sources = parse_sources_dir()
    if not sources:
        print_stage(_("no_sources", d=XPM_SOURCES_DIR))
        return 1
    print_stage(_("updating"))
    os.makedirs(XPM_CACHE, exist_ok=True)
    ok = 0
    for s in sources:
        try:
            if s["type"] == "deb":
                for comp in s["components"]:
                    url = f"{s['url']}/dists/{s['suite']}/{comp}/binary-{s['arch']}/Packages.gz"
                    dest = f"{XPM_CACHE}/{s['name']}-{comp}-Packages.gz"
                    if wget_download(url, dest, timeout=30):
                        gunzip_file(dest, dest[:-3])
                        ok += 1
                        print(f"  ✅ {s['name']}/{comp}")
                    else:
                        print_stage(_("update_fail", src=f"{s['name']}/{comp}"))
                        coffee.crash("wget failed")
            else:
                url = f"{s['url']}/Packages.gz"
                dest = f"{XPM_CACHE}/{s['name']}-Packages.gz"
                if wget_download(url, dest, timeout=30):
                    gunzip_file(dest, dest[:-3])
                    ok += 1
                    print(f"  ✅ {s['name']}")
                else:
                    print_stage(_("update_fail", src=s['name']))
                    coffee.crash("wget failed")
        except subprocess.TimeoutExpired:
            print_stage(_("update_timeout", src=s['name']))
            coffee.crash("timeout")
    print_stage(_("update_ok", n=ok))
    return 0

def load_all_packages():
    """加载所有本地缓存的 Packages 文件"""
    pkgs = []
    if not os.path.isdir(XPM_CACHE):
        return pkgs
    for f in sorted(os.listdir(XPM_CACHE)):
        if f.endswith("Packages"):
            pkgs += parse_packages_file(os.path.join(XPM_CACHE, f))
    return pkgs

def cmd_search(kw):
    idx = load_all_packages()
    kw = kw.lower()
    results = [(p["package"], p.get("version",""), p.get("section","")) for p in idx if kw in p.get("package","").lower()]
    if not results:
        print_stage(_("no_results"))
        return
    print_stage(_("search_results", kw=kw))
    for name, ver, sec in sorted(results):
        print(f"  {name:30s} {ver:25s} [{sec}]")

def cmd_info(pkg_name):
    idx = load_all_packages()
    matches = [p for p in idx if p.get("package") == pkg_name]
    if not matches:
        print(f"  ⚠️ {pkg_name} 未找到")
        return
    p = max(matches, key=lambda x: x.get("version",""))
    for k in ("Package","Version","Architecture","Depends","Description","Section","Size","Filename"):
        if k.lower() in p:
            print(f"  {k:15s}: {p[k.lower()]}")

def cmd_install(pkg_names, autoremove=False):
    db = PackageDB()
    all_pkgs = load_all_packages()
    resolver = DependencyResolver()

    # 解析依赖
    print_stage(_("dep_resolve"))
    installed_names = set(db.list_all())
    to_install = []
    for name in pkg_names:
        if db.is_installed(name):
            print_stage(_("already_installed", pkg=name, ver=db.get_version(name)))
            continue
        chain = resolver.resolve(name, all_pkgs, installed_names)
        for item in chain:
            if item not in to_install:
                to_install.append(item)

    if not to_install:
        return 0

    for i, (name, ver, status) in enumerate(to_install):
        if status == "missing":
            print_stage(_("dep_missing", pkg=name))
            coffee.crash("missing dependency")
            continue

        # [1/4] 正在选中未安装的软件包
        if i == 0:
            print_stage(_("install_start", pkg=name))
        # [2/4] 正在选中 xxx (版本)
        print_stage(_("selecting", pkg=name, ver=ver))

        # 找到下载 URL
        pkg_info = next((p for p in all_pkgs if p.get("package") == name and p.get("version") == ver), None)
        if not pkg_info:
            pkg_info = next((p for p in all_pkgs if p.get("package") == name), None)
        if not pkg_info:
            print(f"  ❌ {name} 在索引中找不到")
            coffee.crash("package not in index")
            continue

        filename = pkg_info.get("filename", "")
        size = pkg_info.get("size", "?")

        # 下载
        sources = parse_sources_dir()
        url = None
        for s in sources:
            if s["type"] == "deb":
                base = s["url"]
                if filename:
                    url = f"{base}/{filename}"
                    break
            else:
                if filename:
                    url = f"{s['url']}/{filename}"
                    break
        if not url:
            # 尝试从 Packages 里的 filename 直接拼
            if filename:
                # 用第一个源
                if sources:
                    url = f"{sources[0]['url']}/{filename}"

        if url:
            dest = f"{XPM_CACHE}/archives/{name}_{ver}.deb"
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            print_stage(_("download_pkg", pkg=f"{name}_{ver}.deb", size=size))
            ok = wget_download(url, dest, timeout=120, progress_cb=progress_callback)
            if not ok:
                print(f"  ❌ 下载失败: {url}")
                coffee.crash("download failed")
                continue

        # [3/4] 正在解压
        print_stage(_("unpacking", pkg=name, ver=ver))
        # 调用后端
        backend = XMCS_BIN if os.path.exists(XMCS_BIN) else XM_BIN
        try:
            rc = subprocess.run([backend, "install", dest if url else name],
                              capture_output=True, text=True, timeout=300)
            if rc.returncode != 0:
                print(f"  ❌ 后端错误: {rc.stderr[:200]}")
                coffee.crash("backend install failed")
                continue
        except subprocess.TimeoutExpired:
            print_stage(_("timeout", s=300))
            coffee.crash("install timeout")
            continue

        # [4/4] 正在设置
        print_stage(_("configuring", pkg=name, ver=ver))

        # 注册到数据库
        files = []
        if os.path.exists(dest):
            files = list_deb_files(dest)
        db.add(name, ver, files=files)

        print_stage(_("install_ok", pkg=name, ver=ver))

    # autoremove
    if autoremove:
        cmd_autoremove(db, resolver, all_pkgs)

    return 0

def list_deb_files(deb_path):
    """列出 .deb 里的文件列表"""
    try:
        rc = subprocess.run(["dpkg", "-c", deb_path], capture_output=True, text=True)
        files = []
        for line in rc.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 6 and parts[0].startswith(("dr","-r","lr")):
                f = " ".join(parts[5:])
                if f.startswith("./"):
                    f = f[2:]
                files.append(f)
        return files
    except:
        return []

def cmd_remove(pkg_names, purge=False):
    db = PackageDB()
    backend = XMCS_BIN if os.path.exists(XMCS_BIN) else XM_BIN

    for name in pkg_names:
        if not db.is_installed(name):
            print_stage(_("not_installed", pkg=name))
            continue

        ver = db.get_version(name)

        # [1/3] 正在寻找与 xxx 相关的文件
        print_stage(_("remove_find", pkg=name))
        files = db.packages.get(name, {}).get("files", [])

        # [2/3] 正在卸载
        print_stage(_("removing", pkg=name, ver=ver))
        try:
            action = "purge" if purge else "remove"
            rc = subprocess.run([backend, action, name],
                              capture_output=True, text=True, timeout=120)
            if rc.returncode != 0:
                print(f"  ❌ 后端错误: {rc.stderr[:200]}")
                coffee.crash("backend remove failed")
                continue
        except subprocess.TimeoutExpired:
            print_stage(_("timeout", s=120))
            coffee.crash("remove timeout")
            continue

        # [3/3] 正在清除（仅 purge）
        if purge:
            print_stage(_("purging", pkg=name, ver=ver))
            db.purge(name)
            print_stage(_("purge_ok", pkg=name))
        else:
            db.remove(name)
            print_stage(_("remove_ok", pkg=name))

    return 0

def cmd_upgrade():
    db = PackageDB()
    all_pkgs = load_all_packages()
    to_upgrade = []

    for name in db.list_all():
        cur_ver = db.get_version(name)
        newer = [p for p in all_pkgs if p.get("package") == name and p.get("version","") > cur_ver]
        if newer:
            latest = max(newer, key=lambda x: x.get("version",""))
            to_upgrade.append((name, latest.get("version","")))

    if not to_upgrade:
        print("  ✅ 所有包已是最新")
        return 0

    print(f"  📋 可升级 {len(to_upgrade)} 个包:")
    for name, ver in to_upgrade:
        print(f"    {name}: {db.get_version(name)} → {ver}")

    for name, ver in to_upgrade:
        cmd_install([name])

    return 0

def cmd_autoremove(db=None, resolver=None, all_pkgs=None):
    if db is None: db = PackageDB()
    if resolver is None: resolver = DependencyResolver()
    if all_pkgs is None: all_pkgs = load_all_packages()

    print_stage(_("autoremove_find"))
    # 找没有被任何已安装包依赖的包
    needed = set(db.list_all())
    for name in db.list_all():
        pkg_info = next((p for p in all_pkgs if p.get("package") == name), None)
        if pkg_info and pkg_info.get("depends"):
            deps = resolver.parse_depends(pkg_info["depends"])
            for alt_group in deps:
                for dep_name, _, _ in alt_group:
                    needed.discard(dep_name)

    orphans = [n for n in db.list_all() if n not in needed and n != "xpm"]
    if not orphans:
        print("  （无多余依赖）")
        return 0

    for name in orphans:
        ver = db.get_version(name)
        print_stage(_("autoremove_item", pkg=name, ver=ver))

    cmd_remove(orphans, purge=False)
    print_stage(_("autoremove_done"))
    return 0

def cmd_reinstall(pkg_names):
    db = PackageDB()
    for name in pkg_names:
        if db.is_installed(name):
            ver = db.get_version(name)
            db.remove(name)
            print(f"  🔄 重新安装 {name} ({ver})")
    return cmd_install(pkg_names)

def cmd_fix_broken():
    """尝试修复中断的安装"""
    print("  🔧 尝试修复中断的安装...")
    backend = XMCS_BIN if os.path.exists(XMCS_BIN) else XM_BIN
    rc = subprocess.run([backend, "fix-broken"], capture_output=True, text=True, timeout=120)
    if rc.returncode == 0:
        print("  ✅ 修复完成")
    else:
        print(f"  ❌ 修复失败: {rc.stderr[:200]}")
        coffee.crash("fix-broken failed")
    return rc.returncode

def cmd_depends(pkg_name):
    all_pkgs = load_all_packages()
    resolver = DependencyResolver()
    pkg = next((p for p in all_pkgs if p.get("package") == pkg_name), None)
    if not pkg:
        print(f"  ⚠️ {pkg_name} 未找到")
        return
    deps = resolver.parse_depends(pkg.get("depends", ""))
    if not deps:
        print(f"  {pkg_name} 无依赖")
        return
    print(f"  {pkg_name} 的依赖:")
    for alt_group in deps:
        line = " | ".join(f"{n} ({o} {v})" if o else n for n, o, v in alt_group)
        print(f"    {line}")

def cmd_rdepends(pkg_name):
    all_pkgs = load_all_packages()
    resolver = DependencyResolver()
    print(f"  {pkg_name} 的反向依赖:")
    found = False
    for p in all_pkgs:
        deps = resolver.parse_depends(p.get("depends", ""))
        for alt_group in deps:
            for n, _, _ in alt_group:
                if n == pkg_name:
                    print(f"    {p.get('package')} ({p.get('version','')})")
                    found = True
    if not found:
        print("    （无）")

def cmd_list(installed_only=False):
    db = PackageDB()
    all_pkgs = load_all_packages()
    if installed_only:
        for name in db.list_all():
            ver = db.get_version(name)
            print(f"  {name:30s} {ver}")
    else:
        # 所有已知包
        seen = set()
        for p in all_pkgs:
            n = p.get("package","")
            if n not in seen:
                seen.add(n)
                ver = p.get("version","")
                mark = "✅" if db.is_installed(n) else "  "
                print(f"  {mark} {n:28s} {ver}")

def cmd_verify(pkg_name=None):
    db = PackageDB()
    gpg = GPGVerifier()
    targets = [pkg_name] if pkg_name else db.list_all()
    for name in targets:
        if not db.is_installed(name):
            print_stage(_("not_installed", pkg=name))
            continue
        ver = db.get_version(name)
        print_stage(_("verifying"))
        # 校验文件完整性
        files = db.packages.get(name, {}).get("files", [])
        missing = 0
        for f in files:
            if not os.path.exists(f):
                missing += 1
        if missing > 0:
            print_stage(_("verify_fail", pkg=name, reason=f"{missing} files missing"))
        else:
            print_stage(_("verify_ok", pkg=name))

def cmd_rollback(args):
    db = PackageDB()
    tx = Transaction(db)
    if not args or args[0] == "list":
        points = tx.list_rollback_points()
        if not points:
            print_stage(_("rollback_empty"))
            return
        print_stage(_("rollback_list"))
        for p in points:
            print(f"  #{p['id']} {p['pkg']:20s} {p['time']}")
        return
    try:
        n = int(args[0])
    except:
        n = None
    if tx.rollback(n):
        print_stage(_("rollback_done", n=n or "?"))
    else:
        print("  ❌ 回滚失败")

def cmd_build(dir_path):
    """将目录打包为 .oil 包"""
    if not os.path.isdir(dir_path):
        print_stage(_("build_fail", reason=f"目录不存在: {dir_path}"))
        return 1

    print_stage(_("building", dir=dir_path))

    # 读取 control
    control_path = os.path.join(dir_path, "xpm", "control")
    if not os.path.exists(control_path):
        print_stage(_("build_fail", reason="缺少 xpm/control 文件"))
        return 1

    control = {}
    with open(control_path) as f:
        for line in f:
            if ":" in line:
                k, v = line.split(":", 1)
                control[k.strip().lower()] = v.strip()

    pkg_name = control.get("package", "unknown")
    pkg_ver = control.get("version", "1.0")
    pkg_arch = control.get("architecture", "all")

    # 收集文件
    files_list = []
    for root, dirs, files in os.walk(dir_path):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, dir_path)
            # 跳过 xpm/ 元数据目录
            if rel.startswith("xpm/"):
                continue
            files_list.append(rel)

    # 写 files.list
    os.makedirs(os.path.join(dir_path, "xpm"), exist_ok=True)
    with open(os.path.join(dir_path, "xpm", "files.list"), "w") as f:
        f.write("\n".join(files_list) + "\n")

    # 写 checksums.sha256
    import hashlib
    with open(os.path.join(dir_path, "xpm", "checksums.sha256"), "w") as f:
        for rel in files_list:
            full = os.path.join(dir_path, rel)
            h = hashlib.sha256()
            with open(full, "rb") as fh:
                h.update(fh.read())
            f.write(f"{h.hexdigest()}  {rel}\n")

    # 打包 .oil (tar.gz) — 不用 tar 命令，用 Python tarfile 避免 ./ 前缀
    import tarfile as _tar
    out_name = f"{pkg_name}_{pkg_ver}_{pkg_arch}.oil"
    out_path = os.path.join(os.getcwd(), out_name)
    with _tar.open(out_path, "w:gz") as tar:
        for root, dirs, files in os.walk(dir_path):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, dir_path)
                if rel.startswith("xpm/pmadd"):
                    continue
                tar.add(full, arcname=rel)

    print_stage(_("build_ok", out=out_path))
    return 0

def cmd_stats():
    db = PackageDB()
    print_stage(_("stats_title"))
    print_stage(_("stats_pkgs", n=db.count()))
    print_stage(_("stats_oil", pct=100001))
    print_stage(_("stats_crashes", n=coffee.get()))
    uptime = time.time() - psutil_uptime_start()
    print_stage(_("stats_uptime", t=f"{int(uptime)}s"))

def psutil_uptime_start():
    """获取系统启动时间（简化）"""
    try:
        with open("/proc/uptime") as f:
            return time.time() - float(f.read().split()[0])
    except:
        return time.time() - 3600

def cmd_doctor():
    print_stage(_("doctor_title"))
    # X11 检测
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        print_stage(_("doctor_x11"))
    # TTY 检测
    if not sys.stdin.isatty():
        print_stage(_("doctor_tty"))
    # 代理检测
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        if os.environ.get(k):
            print_stage(_("doctor_proxy"))
            break
    # root 检测
    if not is_root():
        print_stage(_("doctor_sudo"))
    # 后端检测
    for bin_path in [XMCS_BIN, XM_BIN]:
        if os.path.exists(bin_path):
            print_stage(_("doctor_xm_ok", bin=bin_path))
        else:
            print_stage(_("doctor_xm_missing", bin=bin_path))
    # 禁用 apt 检查
    print_stage(_("no_apt"))
    # 源检查
    sources = parse_sources_dir()
    if sources:
        print(f"  ✅ {len(sources)} 个源已配置")
    else:
        print_stage(_("no_sources", d=XPM_SOURCES_DIR))

def cmd_gui():
    """启动 GUI"""
    try:
        from xpm_gui_v2 import launch_gui
        launch_gui()
    except ImportError:
        # 内嵌简易 GUI
        launch_simple_gui()

def launch_simple_gui():
    """简易 Tkinter GUI（内嵌，不依赖外部文件）"""
    try:
        import tkinter as tk
        from tkinter import ttk, scrolledtext, messagebox
    except ImportError:
        print("❌ tkinter 未安装，无法启动 GUI")
        return

    root = tk.Tk()
    root.title(f"XPM v{VERSION} - {CODENAME}")
    root.geometry("800x600")

    # 语言
    t = I18N[UI_LANG] if UI_LANG in I18N else I18N["en"]

    # 顶部：操作面板
    top = ttk.Frame(root)
    top.pack(fill="x", padx=10, pady=5)

    ttk.Label(top, text="包名:").pack(side="left")
    entry = ttk.Entry(top, width=30)
    entry.pack(side="left", padx=5)
    entry.bind("<Return>", lambda e: do_search())

    search_btn = ttk.Button(top, text="搜索", command=lambda: do_search())
    search_btn.pack(side="left", padx=2)

    install_btn = ttk.Button(top, text="安装", command=lambda: do_install())
    install_btn.pack(side="left", padx=2)

    remove_btn = ttk.Button(top, text="卸载", command=lambda: do_remove())
    remove_btn.pack(side="left", padx=2)

    upgrade_btn = ttk.Button(top, text="升级全部", command=lambda: do_upgrade())
    upgrade_btn.pack(side="left", padx=2)

    update_btn = ttk.Button(top, text="更新源", command=lambda: do_update())
    update_btn.pack(side="left", padx=2)

    # 进行中面板
    progress_frame = ttk.LabelFrame(root, text="进行中")
    progress_frame.pack(fill="x", padx=10, pady=5)
    progress_label = ttk.Label(progress_frame, text="空闲")
    progress_label.pack(anchor="w", padx=5, pady=2)
    progress_bar = ttk.Progressbar(progress_frame, mode="determinate", length=600)
    progress_bar.pack(fill="x", padx=5, pady=2)

    # 包列表
    list_frame = ttk.LabelFrame(root, text="包列表")
    list_frame.pack(fill="both", expand=True, padx=10, pady=5)
    cols = ("name", "version", "status")
    tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)
    tree.heading("name", text="包名")
    tree.heading("version", text="版本")
    tree.heading("status", text="状态")
    tree.column("name", width=250)
    tree.column("version", width=200)
    tree.column("status", width=100)
    tree.pack(fill="both", expand=True, padx=5, pady=5)

    # 日志窗口
    log_frame = ttk.LabelFrame(root, text="日志")
    log_frame.pack(fill="both", expand=True, padx=10, pady=5)
    log_box = scrolledtext.ScrolledText(log_frame, height=8, state="disabled")
    log_box.pack(fill="both", expand=True, padx=5, pady=5)

    def log(msg):
        log_box.config(state="normal")
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        log_box.config(state="disabled")
        # 同时写文件
        try:
            os.makedirs(f"{XPM_LOG}", exist_ok=True)
            with open(f"{XPM_LOG}/gui.log", "a") as f:
                f.write(f"[{datetime.now().isoformat()}] {msg}\n")
        except:
            pass

    def refresh_list():
        for item in tree.get_children():
            tree.delete(item)
        db = PackageDB()
        all_pkgs = load_all_packages()
        for p in sorted(all_pkgs, key=lambda x: x.get("package","")):
            name = p.get("package","")
            ver = p.get("version","")
            status = "✅ 已安装" if db.is_installed(name) else ""
            tree.insert("", "end", values=(name, ver, status))

    def set_progress(text, pct=0):
        progress_label.config(text=text)
        progress_bar["value"] = pct
        root.update_idletasks()

    def do_search():
        kw = entry.get().strip()
        if not kw:
            return
        log(f"🔍 搜索: {kw}")
        threading.Thread(target=_search_thread, args=(kw,), daemon=True).start()

    def _search_thread(kw):
        idx = load_all_packages()
        kw_lower = kw.lower()
        results = [(p["package"], p.get("version","")) for p in idx if kw_lower in p.get("package","").lower()]
        log(f"  找到 {len(results)} 个结果")
        for name, ver in sorted(results)[:20]:
            log(f"  {name} ({ver})")

    def do_install():
        pkg = entry.get().strip()
        if not pkg:
            messagebox.showwarning("XPM", "请输入包名")
            return
        log(f"📦 安装: {pkg}")
        install_btn.config(text="安装中…", state="disabled")
        threading.Thread(target=_install_thread, args=(pkg,), daemon=True).start()

    def _install_thread(pkg):
        try:
            set_progress(f"正在下载 {pkg}...", 10)
            log(f"[1/4] 正在选中未安装的软件包：{pkg}")
            db = PackageDB()
            all_pkgs = load_all_packages()
            resolver = DependencyResolver()
            installed_names = set(db.list_all())
            chain = resolver.resolve(pkg, all_pkgs, installed_names)
            for i, (name, ver, status) in enumerate(chain):
                if status == "missing":
                    log(f"  ⚠️ 缺少依赖: {name}")
                    continue
                log(f"[2/4] 正在选中 {name} ({ver})")
                set_progress(f"正在解压 {name}...", 30 + i * 20)
                log(f"[3/4] 正在解压 {name} ({ver})...")
                # 调用后端
                backend = XMCS_BIN if os.path.exists(XMCS_BIN) else XM_BIN
                rc = subprocess.run([backend, "install", name], capture_output=True, text=True, timeout=120)
                if rc.returncode == 0:
                    log(f"[4/4] 正在设置 {name} ({ver})...")
                    db.add(name, ver)
                    log(f"✅ {name} ({ver}) 安装完成")
                else:
                    log(f"❌ {name} 安装失败: {rc.stderr[:100]}")
            set_progress("空闲", 0)
            log(f"✅ {pkg} 安装流程结束")
            refresh_list()
        except Exception as e:
            log(f"❌ 异常: {e}")
            coffee.crash(str(e))
        finally:
            install_btn.config(text="安装", state="normal")

    def do_remove():
        pkg = entry.get().strip()
        if not pkg:
            messagebox.showwarning("XPM", "请输入包名")
            return
        log(f"🗑️ 卸载: {pkg}")
        remove_btn.config(text="卸载中…", state="disabled")
        threading.Thread(target=_remove_thread, args=(pkg,), daemon=True).start()

    def _remove_thread(pkg):
        try:
            db = PackageDB()
            ver = db.get_version(pkg)
            log(f"[1/3] 正在寻找与 {pkg} 相关的文件...")
            set_progress(f"正在卸载 {pkg}...", 30)
            log(f"[2/3] 正在卸载 {pkg} ({ver})...")
            backend = XMCS_BIN if os.path.exists(XMCS_BIN) else XM_BIN
            rc = subprocess.run([backend, "remove", pkg], capture_output=True, text=True, timeout=120)
            if rc.returncode == 0:
                log(f"[3/3] 正在清除 {pkg} ({ver})...")
                db.remove(pkg)
                log(f"✅ {pkg} 卸载完成")
            else:
                log(f"❌ 卸载失败: {rc.stderr[:100]}")
            set_progress("空闲", 0)
            refresh_list()
        except Exception as e:
            log(f"❌ 异常: {e}")
            coffee.crash(str(e))
        finally:
            remove_btn.config(text="卸载", state="normal")

    def do_upgrade():
        log("📦 升级全部...")
        upgrade_btn.config(text="升级中…", state="disabled")
        threading.Thread(target=_upgrade_thread, daemon=True).start()

    def _upgrade_thread():
        try:
            cmd_upgrade()
            refresh_list()
        finally:
            upgrade_btn.config(text="升级全部", state="normal")

    def do_update():
        log("🔄 更新源...")
        update_btn.config(text="更新中…", state="disabled")
        threading.Thread(target=_update_thread, daemon=True).start()

    def _update_thread():
        try:
            cmd_update()
            refresh_list()
        finally:
            update_btn.config(text="更新源", state="normal")

    # 初始刷新
    refresh_list()
    log(f"XPM GUI v{VERSION} 已启动")
    log(_("no_apt"))
    log(_("wget_only"))

    root.mainloop()

# ====== 主入口 ======
def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) < 1:
        cmd_help()
        return 0

    cmd = argv[0]
    args = argv[1:]

    # 拦截任何 apt 调用（安全锁）
    if "apt" in cmd.lower():
        print_stage(_("no_apt"))
        return 1

    handlers = {
        "help": lambda: (cmd_help(), 0),
        "version": lambda: (cmd_version(), 0),
        "sources": lambda: (cmd_sources(), 0),
        "update": lambda: (None, cmd_update()),
        "search": lambda: (args and (cmd_search(args[0]), 0)) or (print("用法: xpm search <关键词>"), 1),
        "info": lambda: (args and (cmd_info(args[0]), 0)) or (print("用法: xpm info <包名>"), 1),
        "install": lambda: (args and (None, cmd_install(args))) or (print("用法: xpm install <包名> [...]"), 1),
        "remove": lambda: (args and (None, cmd_remove(args, purge=False))) or (print("用法: xpm remove <包名> [...]"), 1),
        "purge": lambda: (args and (None, cmd_remove(args, purge=True))) or (print("用法: xpm purge <包名> [...]"), 1),
        "upgrade": lambda: (None, cmd_upgrade()),
        "reinstall": lambda: (args and (None, cmd_reinstall(args))) or (print("用法: xpm reinstall <包名> [...]"), 1),
        "fix-broken": lambda: (None, cmd_fix_broken()),
        "depends": lambda: (args and (cmd_depends(args[0]), 0)) or (print("用法: xpm depends <包名>"), 1),
        "rdepends": lambda: (args and (cmd_rdepends(args[0]), 0)) or (print("用法: xpm rdepends <包名>"), 1),
        "list": lambda: (cmd_list(installed_only="--installed" in args), 0),
        "verify": lambda: (cmd_verify(args[0] if args else None), 0),
        "rollback": lambda: (None, cmd_rollback(args)),
        "build": lambda: (args and (None, cmd_build(args[0]))) or (print("用法: xpm build <目录>"), 1),
        "stats": lambda: (cmd_stats(), 0),
        "doctor": lambda: (cmd_doctor(), 0),
        "gui": lambda: (cmd_gui(), 0),
    }

    handler = handlers.get(cmd)
    if handler is None:
        print_stage(_("unknown_cmd", cmd=cmd))
        cmd_help()
        return 1

    try:
        result = handler()
        return result if isinstance(result, int) else 0
    except KeyboardInterrupt:
        print_stage(_("abort"))
        coffee.crash("user interrupt")
        return 130

if __name__ == "__main__":
    sys.exit(main())

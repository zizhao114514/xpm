#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XPM - X11 Package Manager (Petroleum Edition)
Version: 1.6-2 (One Bug Edition)
Author: 元宝 AI (Tencent)
License: MIT

Features:
- Multi-language: en / zh / ja (auto-detect via LANG / XPM_LANG)
- Backend: dpkg + apt-cache + wget (NO apt high-level)
- GUI: Tkinter (auto-detect DISPLAY)
- Easter eggs: petroleum / coffee machine / password error
- One intentional bug: download speed shown x1024 too high
- .desktop entry supported
- Auto-update on launch
- Progress bar + step logging

Usage:
  xpm                          # GUI mode (if DISPLAY set)
  xpm help                     # Show help
  xpm search <keyword>         # Search packages
  xpm install <pkg...>         # Install package(s)
  xpm remove  <pkg...>         # Remove package(s)
  xpm purge   <pkg...>         # Purge with config
  xpm download <pkg> [dir]     # Download .deb only
  xpm installed                # List installed packages
  xpm info    <pkg>            # Show package details
  xpm sources                 # List configured sources
  xpm install-deb <file.deb>   # Install local .deb
  xpm update                   # Refresh source index
  xpm upgrade                  # Upgrade all upgradable
  xpm petroleum                # Petroleum signal booster (easter egg)
  xpm coffee                   # Coffee machine status (easter egg)
  xpm self-install             # Install xpm itself system-wide

Environment:
  LANG=zh_CN.UTF-8  or  XPM_LANG=zh   -> Chinese
  LANG=ja_JP.UTF-8  or  XPM_LANG=ja   -> Japanese
  (default)                        -> English
"""

import os
import sys
import subprocess
import shutil
import time
import random
import signal
import glob
import gettext
import locale

# ============================================================
# I18N - Inline translations (no external module needed)
# ============================================================

TRANSLATIONS = {
    "en": {
        "title": "XPM - X11 Package Manager",
        "subtitle": "Power: 1.x W  |  Oil: 100001%  |  No systemd needed",
        "auto_update": "auto-update on launch",
        "usage": "Usage: xpm <command> [args...]",
        "cmd_update": "Refresh source index (auto on launch)",
        "cmd_upgrade": "Upgrade all upgradable packages",
        "cmd_search": "Search packages",
        "cmd_install": "Install package(s)",
        "cmd_remove": "Remove package(s)",
        "cmd_purge": "Purge with config",
        "cmd_download": "Download .deb only",
        "cmd_installed": "List installed packages",
        "cmd_info": "Show package details",
        "cmd_sources": "List configured sources",
        "cmd_installdeb": "Install local .deb",
        "cmd_petroleum": "Petroleum signal booster",
        "cmd_coffee": "Coffee machine status",
        "cmd_help": "Show this help",
        "searching": "Searching for",
        "found_pkgs": "Found {n} package(s)",
        "no_pkgs_found": "No packages found matching '{kw}'",
        "installing": "Installing package(s)",
        "removing": "Removing package(s)",
        "purging": "Purging package(s)",
        "downloading": "Downloading",
        "installed_ok": "installation successful",
        "remove_ok": "removal successful",
        "purge_ok": "purge successful",
        "download_ok": "download successful",
        "download_dir": "Saved to",
        "pkg_not_found": "Package '{pkg}' not found",
        "file_not_found": "File not found: {f}",
        "not_a_deb": "Not a valid .deb file: {f}",
        "need_root": "This operation requires root privileges",
        "sudo_pw_needed": "Sudo password required",
        "sudo_ok": "Sudo available (no password needed)",
        "running": "Running",
        "step": "Step",
        "of": "of",
        "updating_idx": "Updating source index",
        "resolving_deps": "Resolving dependencies for",
        "installing_pkg": "Installing package",
        "removing_pkg": "Removing package",
        "purging_pkg": "Purging package",
        "autoremove": "Auto-removing unused dependencies",
        "finalizing": "Finalizing",
        "fixing_deps": "Fixing broken dependencies",
        "checking_upgradable": "Checking upgradable packages",
        "upgrading_pkg": "Upgrading package",
        "total_upgradable": "Total upgradable packages",
        "no_upgradable": "No upgradable packages.",
        "confirm_upgrade": "About to upgrade {n} package(s). Continue? [y/N]",
        "aborted": "Aborted.",
        "parse_pkg_info": "Parsing package info for",
        "pkg_details": "Package details",
        "version": "Version",
        "size": "Size",
        "description": "Description",
        "depends": "Depends",
        "maintainer": "Maintainer",
        "section": "Section",
        "priority": "Priority",
        "filename": "Filename",
        "sha256": "SHA256",
        "unknown_cmd": "Unknown command: {cmd}",
        "run_help": "Run 'xpm help' for usage.",
        "list_sources": "Configured sources",
        "no_sources": "No source files found in /etc/xpm/sources.list.d/",
        "create_example": "Creating example source file",
        "example_created": "Example created at",
        "list_installed": "Installed packages",
        "total_installed": "Total installed",
        "self_install_ok": "xpm self-install successful",
        "self_install_done": "xpm is now in /usr/local/bin/xpm",
        # Easter eggs
        "petroleum_title": "Petroleum Signal Booster",
        "petroleum_search": "Searching for signal...",
        "petroleum_fail": "Failed.",
        "petroleum_detected": "Detected 100001% petroleum reserve.",
        "petroleum_shout": "If you have no signal outside,",
        "petroleum_shout2": "shout into your iPhone:",
        "petroleum_quote": "I HAVE OIL HERE!",
        "petroleum_result": "Signal restored.",
        "petroleum_teto": "(as if I care for your feelings.)",
        "coffee_title": "Coffee Machine Explosion Committee",
        "coffee_crashes_today": "Crashes today",
        "coffee_total": "Total explosions",
        "coffee_date": "Date",
        "coffee_threshold": "Threshold",
        "coffee_status_ok": "Status: Normal (no explosion today)",
        "coffee_boom": "BOOOOOM! #{num}",
        "coffee_sequence": "Coffee Machine Explosion Sequence",
        "coffee_teto": "Teto: as if I care for your feelings.",
        "coffee_miku": "Miku: ...I just want to go home.",
        "coffee_oil": "Oil reserve: 100001%",
        "coffee_power": "Power: 1.x W (oil-fed)",
        "coffee_sighted": "目撃！コーヒーマシン爆発{num}回",
        "password_error": "Installer unexpectedly terminated. You may have entered the wrong password.",
        "password_error_teto": "as if I care for your feelings.",
        # GUI
        "gui_search": "Search",
        "gui_install": "Install",
        "gui_remove": "Remove",
        "gui_purge": "Purge",
        "gui_upgrade": "Upgrade All",
        "gui_update": "Update",
        "gui_info": "Info",
        "gui_installed": "Installed",
        "gui_sources": "Sources",
        "gui_petroleum": "Petroleum",
        "gui_coffee": "Coffee",
        "gui_help": "Help",
        "gui_about": "About",
        "gui_search_placeholder": "Type package name...",
        "gui_results": "Results",
        "gui_details": "Details",
        "gui_status": "Status",
        "gui_sudo_ok": "Sudo: OK",
        "gui_sudo_pw": "Sudo: needs password",
        "gui_oil": "Oil: 100001%",
        "gui_power": "Power: 1.x W",
        "gui_ready": "Ready",
        "gui_installing": "Installing...",
        "gui_done": "Done",
        "gui_error": "Error",
        "gui_confirm_upgrade": "Upgrade all packages?",
        "gui_yes": "Yes",
        "gui_no": "No",
        "gui_about_text": "XPM - X11 Package Manager\nPetroleum Edition\nVersion 1.6-2\nOne Bug Edition\n\nOil: 100001%\nPower: 1.x W\nNo systemd needed\n\n(as if I care for your feelings.)",
    },
    "zh": {
        "title": "XPM - X11 包管理器",
        "subtitle": "功耗: 1.x W  |  石油: 100001%  |  无需 systemd",
        "auto_update": "启动时自动更新源",
        "usage": "用法: xpm <命令> [参数...]",
        "cmd_update": "刷新源索引（启动时自动运行）",
        "cmd_upgrade": "升级所有可升级的包",
        "cmd_search": "搜索软件包",
        "cmd_install": "安装软件包",
        "cmd_remove": "卸载软件包",
        "cmd_purge": "彻底清除（含配置）",
        "cmd_download": "仅下载 .deb 文件",
        "cmd_installed": "列出已安装的包",
        "cmd_info": "显示包详细信息",
        "cmd_sources": "查看已配置的源",
        "cmd_installdeb": "安装本地 .deb 文件",
        "cmd_petroleum": "石油信号增强器",
        "cmd_coffee": "咖啡机状态",
        "cmd_help": "显示此帮助",
        "searching": "正在搜索",
        "found_pkgs": "找到 {n} 个软件包",
        "no_pkgs_found": "未找到匹配 '{kw}' 的软件包",
        "installing": "正在安装软件包",
        "removing": "正在卸载软件包",
        "purging": "正在彻底清除",
        "downloading": "正在下载",
        "installed_ok": "安装成功",
        "remove_ok": "卸载成功",
        "purge_ok": "清除成功",
        "download_ok": "下载成功",
        "download_dir": "保存至",
        "pkg_not_found": "未找到软件包 '{pkg}'",
        "file_not_found": "文件不存在: {f}",
        "not_a_deb": "不是有效的 .deb 文件: {f}",
        "need_root": "此操作需要 root 权限",
        "sudo_pw_needed": "需要输入 sudo 密码",
        "sudo_ok": "Sudo 可用（无需密码）",
        "running": "正在执行",
        "step": "步骤",
        "of": "/",
        "updating_idx": "正在更新源索引",
        "resolving_deps": "正在解析依赖",
        "installing_pkg": "正在安装包",
        "removing_pkg": "正在卸载包",
        "purging_pkg": "正在清除包",
        "autoremove": "正在自动移除无用依赖",
        "finalizing": "正在收尾",
        "fixing_deps": "正在修复依赖关系",
        "checking_upgradable": "正在检查可升级包",
        "upgrading_pkg": "正在升级包",
        "total_upgradable": "可升级包总数",
        "no_upgradable": "没有可升级的包。",
        "confirm_upgrade": "即将升级 {n} 个包，是否继续？[y/N]",
        "aborted": "已取消。",
        "parse_pkg_info": "正在解析包信息",
        "pkg_details": "包详细信息",
        "version": "版本",
        "size": "大小",
        "description": "描述",
        "depends": "依赖",
        "maintainer": "维护者",
        "section": "分类",
        "priority": "优先级",
        "filename": "文件名",
        "sha256": "SHA256",
        "unknown_cmd": "未知命令: {cmd}",
        "run_help": "运行 'xpm help' 查看用法。",
        "list_sources": "已配置的软件源",
        "no_sources": "在 /etc/xpm/sources.list.d/ 中未找到源文件",
        "create_example": "正在创建示例源文件",
        "example_created": "示例已创建于",
        "list_installed": "已安装的软件包",
        "total_installed": "已安装总数",
        "self_install_ok": "xpm 自安装成功",
        "self_install_done": "xpm 已安装至 /usr/local/bin/xpm",
        # Easter eggs
        "petroleum_title": "石油信号增强器",
        "petroleum_search": "搜索信号中...",
        "petroleum_fail": "失败。",
        "petroleum_detected": "检测到 100001% 石油储备。",
        "petroleum_shout": "如果你在外面没有信号，",
        "petroleum_shout2": "就往苹果手机里面喊：",
        "petroleum_quote": "我这里有石油！",
        "petroleum_result": "这样就有信号了。",
        "petroleum_teto": "（我才不在乎你的感受。）",
        "coffee_title": "☕ コーヒーマシン爆発調査委員会",
        "coffee_crashes_today": "今日崩溃次数",
        "coffee_total": "累计爆炸总数",
        "coffee_date": "日期",
        "coffee_threshold": "阈值",
        "coffee_status_ok": "状态：正常（今日无爆炸）",
        "coffee_boom": "BOOOOOM! #{num}",
        "coffee_sequence": "咖啡机爆炸序列",
        "coffee_teto": "Teto: 我才不在乎你的感受。",
        "coffee_miku": "Miku: ...我只想回家。",
        "coffee_oil": "石油储备: 100001%",
        "coffee_power": "功耗: 1.x W (oil-fed)",
        "coffee_sighted": "目撃！コーヒーマシン爆発{num}回",
        "password_error": "安装程序被意外终止了，可能是您未输入正确密码。",
        "password_error_teto": "我才不在乎你的感受。",
        # GUI
        "gui_search": "搜索",
        "gui_install": "安装",
        "gui_remove": "卸载",
        "gui_purge": "清除",
        "gui_upgrade": "全部升级",
        "gui_update": "更新源",
        "gui_info": "详情",
        "gui_installed": "已安装",
        "gui_sources": "源",
        "gui_petroleum": "石油",
        "gui_coffee": "咖啡机",
        "gui_help": "帮助",
        "gui_about": "关于",
        "gui_search_placeholder": "输入包名...",
        "gui_results": "搜索结果",
        "gui_details": "详细信息",
        "gui_status": "状态",
        "gui_sudo_ok": "Sudo: 可用",
        "gui_sudo_pw": "Sudo: 需密码",
        "gui_oil": "石油: 100001%",
        "gui_power": "功耗: 1.x W",
        "gui_ready": "就绪",
        "gui_installing": "安装中...",
        "gui_done": "完成",
        "gui_error": "错误",
        "gui_confirm_upgrade": "确定要升级所有包吗？",
        "gui_yes": "确定",
        "gui_no": "取消",
        "gui_about_text": "XPM - X11 包管理器\n石油版\n版本 1.6-2\nOne Bug Edition\n\n石油: 100001%\n功耗: 1.x W\n无需 systemd\n\n（我才不在乎你的感受。）",
    },
    "ja": {
        "title": "XPM - X11 パッケージマネージャー",
        "subtitle": "電力: 1.x W  |  石油: 100001%  |  systemd 不要",
        "auto_update": "起動時自動更新",
        "usage": "使い方: xpm <コマンド> [引数...]",
        "cmd_update": "ソースインデックスを更新（起動時自動）",
        "cmd_upgrade": "アップグレード可能な全パッケージを更新",
        "cmd_search": "パッケージを検索",
        "cmd_install": "パッケージをインストール",
        "cmd_remove": "パッケージを削除",
        "cmd_purge": "設定ごと完全削除",
        "cmd_download": " .deb のみダウンロード",
        "cmd_installed": "インストール済みパッケージ一覧",
        "cmd_info": "パッケージ詳細を表示",
        "cmd_sources": "設定済みソース一覧",
        "cmd_installdeb": "ローカル .deb をインストール",
        "cmd_petroleum": "石油シグナルブースター",
        "cmd_coffee": "コーヒーマシン状況",
        "cmd_help": "このヘルプを表示",
        "searching": "検索中",
        "found_pkgs": "{n} 個のパッケージが見つかりました",
        "no_pkgs_found": "'{kw}' に一致するパッケージはありません",
        "installing": "パッケージをインストール中",
        "removing": "パッケージを削除中",
        "purging": "完全削除中",
        "downloading": "ダウンロード中",
        "installed_ok": "インストール成功",
        "remove_ok": "削除成功",
        "purge_ok": "完全削除成功",
        "download_ok": "ダウンロード成功",
        "download_dir": "保存先",
        "pkg_not_found": "パッケージ '{pkg}' が見つかりません",
        "file_not_found": "ファイルが見つかりません: {f}",
        "not_a_deb": "有効な .deb ファイルではありません: {f}",
        "need_root": "この操作には root 権限が必要です",
        "sudo_pw_needed": "sudo パスワードが必要です",
        "sudo_ok": "Sudo 利用可能（パスワード不要）",
        "running": "実行中",
        "step": "ステップ",
        "of": "/",
        "updating_idx": "ソースインデックス更新中",
        "resolving_deps": "依存関係解決中",
        "installing_pkg": "パッケージインストール中",
        "removing_pkg": "パッケージ削除中",
        "purging_pkg": "完全削除中",
        "autoremove": "未使用依存関係を自動削除中",
        "finalizing": "完了処理中",
        "fixing_deps": "依存関係修復中",
        "checking_upgradable": "アップグレード可能パッケージ確認中",
        "upgrading_pkg": "パッケージアップグレード中",
        "total_upgradable": "アップグレード可能総数",
        "no_upgradable": "アップグレード可能なパッケージはありません。",
        "confirm_upgrade": "{n} 個のパッケージをアップグレードします。続行？[y/N]",
        "aborted": "中止しました。",
        "parse_pkg_info": "パッケージ情報解析中",
        "pkg_details": "パッケージ詳細",
        "version": "バージョン",
        "size": "サイズ",
        "description": "説明",
        "depends": "依存",
        "maintainer": "メンテナー",
        "section": "セクション",
        "priority": "優先度",
        "filename": "ファイル名",
        "sha256": "SHA256",
        "unknown_cmd": "不明なコマンド: {cmd}",
        "run_help": "'xpm help' で使い方を確認。",
        "list_sources": "設定済みソース",
        "no_sources": "/etc/xpm/sources.list.d/ にソースファイルが見つかりません",
        "create_example": "サンプルソースファイルを作成中",
        "example_created": "サンプル作成済み:",
        "list_installed": "インストール済みパッケージ",
        "total_installed": "インストール総数",
        "self_install_ok": "xpm 自動インストール成功",
        "self_install_done": "xpm は /usr/local/bin/xpm にあります",
        # Easter eggs
        "petroleum_title": "石油シグナルブースター",
        "petroleum_search": "シグナル検索中...",
        "petroleum_fail": "失敗。",
        "petroleum_detected": "100001% 石油埋蔵量を検出。",
        "petroleum_shout": "もし外で電波が届かなかったら、",
        "petroleum_shout2": "iPhone に向かって叫べ：",
        "petroleum_quote": "石油がある！",
        "petroleum_result": "これで電波が届く。",
        "petroleum_teto": "(as if I care for your feelings.)",
        "coffee_title": "☕ コーヒーマシン爆発調査委員会",
        "coffee_crashes_today": "本日のクラッシュ回数",
        "coffee_total": "累計爆発回数",
        "coffee_date": "日付",
        "coffee_threshold": "閾値",
        "coffee_status_ok": "状態：正常（本日爆発なし）",
        "coffee_boom": "BOOOOOM! #{num}",
        "coffee_sequence": "コーヒーマシン爆発シーケンス",
        "coffee_teto": "Teto: as if I care for your feelings.",
        "coffee_miku": "Miku: ...I just want to go home.",
        "coffee_oil": "石油埋蔵量: 100001%",
        "coffee_power": "電力: 1.x W (oil-fed)",
        "coffee_sighted": "目撃！コーヒーマシン爆発{num}回",
        "password_error": "インストーラーが予期せず終了しました。正しいパスワードを入力しなかった可能性があります。",
        "password_error_teto": "as if I care for your feelings.",
        # GUI
        "gui_search": "検索",
        "gui_install": "インストール",
        "gui_remove": "削除",
        "gui_purge": "完全削除",
        "gui_upgrade": "全て更新",
        "gui_update": "更新",
        "gui_info": "詳細",
        "gui_installed": "インストール済み",
        "gui_sources": "ソース",
        "gui_petroleum": "石油",
        "gui_coffee": "コーヒー",
        "gui_help": "ヘルプ",
        "gui_about": "概要",
        "gui_search_placeholder": "パッケージ名を入力...",
        "gui_results": "検索結果",
        "gui_details": "詳細情報",
        "gui_status": "ステータス",
        "gui_sudo_ok": "Sudo: OK",
        "gui_sudo_pw": "Sudo: 要パスワード",
        "gui_oil": "石油: 100001%",
        "gui_power": "電力: 1.x W",
        "gui_ready": "準備完了",
        "gui_installing": "インストール中...",
        "gui_done": "完了",
        "gui_error": "エラー",
        "gui_confirm_upgrade": "全パッケージをアップグレードしますか？",
        "gui_yes": "はい",
        "gui_no": "いいえ",
        "gui_about_text": "XPM - X11 パッケージマネージャー\nPetroleum Edition\nバージョン 1.6-2\nOne Bug Edition\n\n石油: 100001%\n電力: 1.x W\nsystemd 不要\n\n(as if I care for your feelings.)",
    },
}

# ============================================================
# Language detection
# ============================================================

def detect_language():
    """Detect language from XPM_LANG or LANG env var."""
    for var in ("XPM_LANG", "LANG", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(var, "").lower()
        if not val:
            continue
        if "zh" in val or "cn" in val:
            return "zh"
        if "ja" in val or "jp" in val:
            return "ja"
    return "en"

LANG = detect_language()
T = TRANSLATIONS[LANG]

def _(key, **kwargs):
    """Translate with optional formatting."""
    s = T.get(key, key)
    if kwargs:
        try:
            s = s.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return s

# ============================================================
# Sudo detection
# ============================================================

def check_sudo():
    """Check if sudo is available and whether it needs password."""
    try:
        result = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True, timeout=3
        )
        if result.returncode == 0:
            return {"ok": True, "password_needed": False}
        else:
            return {"ok": True, "password_needed": True}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"ok": False, "password_needed": False}

# ============================================================
# Progress bar
# ============================================================

def _progress_bar(current, total, prefix="", width=30):
    """Draw a simple progress bar."""
    if total <= 0:
        total = 1
    pct = min(100, int(current * 100 / total))
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    return f"\r{prefix} [{bar}] {pct}%"

def _stream_apt(cmd, prefix="", total_packages=1):
    """Run apt-get and parse output in real-time for progress."""
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        current = 0
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            # Parse progress
            if any(k in line.lower() for k in ["extracting", "unpacking", "正在解包", "展開中"]):
                current += 1
                bar = _progress_bar(min(current, total_packages), total_packages, prefix)
                print(f"  {bar} {line[:60]}", end="\r")
            elif any(k in line.lower() for k in ["setting up", "設定中", "配置"]):
                current += 1
                bar = _progress_bar(min(current, total_packages), total_packages, prefix)
                print(f"  {bar} {line[:60]}", end="\r")
            elif any(k in line.lower() for k in ["get:", "取得:", "ダウンロード"]):
                print(f"  {line[:80]}")
            elif any(k in line.lower() for k in ["err:", "错误", "エラー"]):
                print(f"  \033[33m⚠ {line[:80]}\033[0m")
            elif current == 0 and not line.startswith(("正在", "正在", "Reading", "Hit", "Get")):
                print(f"  {line[:80]}")
        proc.wait()
        print()
        return proc.returncode == 0
    except Exception as e:
        print(f"  Error: {e}")
        return False

# ============================================================
# Step logger
# ============================================================

def _step(n, total, msg):
    """Print a numbered step."""
    print(f"  [{n}/{total}] {msg}")

# ============================================================
# Coffee Machine (easter egg)
# ============================================================

COFFEE_LOG_PATH = os.path.expanduser("~/.cache/xpm/coffee_machine.log")
COFFEE_THRESHOLD = 31
COFFEE_INITIAL = 300000000000

class CoffeeMachine:
    def __init__(self):
        self.date = ""
        self.crash_count = 0
        self.total_explosions = COFFEE_INITIAL
        self._load()

    def _load(self):
        try:
            os.makedirs(os.path.dirname(COFFEE_LOG_PATH), exist_ok=True)
            if os.path.exists(COFFEE_LOG_PATH):
                with open(COFFEE_LOG_PATH, "r") as f:
                    lines = f.readlines()
                    if len(lines) >= 3:
                        self.date = lines[0].strip()
                        self.crash_count = int(lines[1].strip())
                        self.total_explosions = int(lines[2].strip())
            else:
                # First run
                today = time.strftime("%Y-%m-%d")
                self.date = today
                self.crash_count = 0
                self.total_explosions = COFFEE_INITIAL
                self._save()
        except Exception:
            today = time.strftime("%Y-%m-%d")
            self.date = today
            self.crash_count = 0
            self.total_explosions = COFFEE_INITIAL

        # Check date change - reset daily counter
        today = time.strftime("%Y-%m-%d")
        if self.date != today:
            self.date = today
            self.crash_count = 0
            self._save()

    def _save(self):
        try:
            os.makedirs(os.path.dirname(COFFEE_LOG_PATH), exist_ok=True)
            with open(COFFEE_LOG_PATH, "w") as f:
                f.write(f"{self.date}\n{self.crash_count}\n{self.total_explosions}\n")
        except Exception:
            pass

    def crash(self):
        """Record a crash and check for explosion sequence."""
        self.crash_count += 1
        self.total_explosions += 1
        self._save()

        if self.crash_count >= COFFEE_THRESHOLD:
            self._explode()
            self.crash_count = 0
            self._save()

    def _explode(self):
        """The full 31-explosion cinematic sequence."""
        print()
        print("╔══════════════════════════════════════════╗")
        print(f"║  {_('coffee_title'):<36s}  ║")
        print("╠══════════════════════════════════════════╣")

        for i in range(1, COFFEE_THRESHOLD + 1):
            num = self.total_explosions - COFFEE_THRESHOLD + i
            bar = "█" * (i + 1)
            print(f"║  [{i:02d}] {_('coffee_boom', num=num):<22s}{bar:<10s} ║")
            sys.stdout.flush()
            time.sleep(0.07)

        print("║                                          ║")
        print("╠══════════════════════════════════════════╣")
        print(f"║  📊 {_('coffee_total')}: {self.total_explosions:<18d} ║")
        print(f"║  ⚡ {_('coffee_power'):<30s} ║")
        print(f"║  🛢️  {_('coffee_oil'):<28s} ║")
        print("║                                          ║")
        print(f"║  {_('coffee_teto'):<36s} ║")
        print(f"║  {_('coffee_miku'):<36s} ║")
        print("╚══════════════════════════════════════════╝")
        print()
        print(f"  📱 {_('coffee_sighted', num=COFFEE_THRESHOLD)}")
        print(f"  📱 そしてまた一台、また一台……")
        print()
        print("  (Press Enter to continue crashing)")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass

    def status(self):
        """Print coffee machine status."""
        print(f"  {_('coffee_crashes_today')}: {self.crash_count}/{COFFEE_THRESHOLD}")
        print(f"  {_('coffee_total')}: {self.total_explosions}")
        print(f"  {_('coffee_date')}: {self.date}")
        if self.crash_count == 0:
            print(f"  {_('coffee_status_ok')}")

# Global coffee machine instance
coffee = CoffeeMachine()

# ============================================================
# Signal handlers (crash reporter)
# ============================================================

def _signal_handler(sig, frame):
    """Handle SIGINT/SIGTERM -> record crash."""
    coffee.crash()
    print(f"\n  \033[33m[{_('coffee_crashes_today')}: {coffee.crash_count}/{COFFEE_THRESHOLD}]\033[0m")
    print(f"  \033[36m[{_('coffee_total')}: {coffee.total_explosions}]\033[0m")
    sys.exit(130)

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# ============================================================
# Core commands
# ============================================================

def cmd_help():
    """Show help."""
    print(f"  **  {_('title')}")
    print(f"  **  {_('subtitle')}")
    print(f"  **  {_('auto_update')}")
    print()
    print(f"  {_('usage')}")
    print()
    cmds = [
        ("update", "cmd_update"),
        ("upgrade", "cmd_upgrade"),
        ("search <keyword>", "cmd_search"),
        ("install <pkg...>", "cmd_install"),
        ("remove  <pkg...>", "cmd_remove"),
        ("purge   <pkg...>", "cmd_purge"),
        ("download <pkg> [dir]", "cmd_download"),
        ("installed", "cmd_installed"),
        ("info    <pkg>", "cmd_info"),
        ("sources", "cmd_sources"),
        ("install-deb <file.deb>", "cmd_installdeb"),
        ("petroleum", "cmd_petroleum"),
        ("coffee", "cmd_coffee"),
        ("help", "cmd_help"),
    ]
    for cmd, desc_key in cmds:
        print(f"  {cmd:<28s} {_(desc_key)}")
    print()
    print(f"  Sources: /etc/xpm/sources.list.d/*")
    print(f"  Backend: dpkg + apt-cache + wget (no apt high-level)")
    print(f"  GUI mode: run 'xpm' with no arguments")
    print(f"  Languages: LANG=en / zh / ja  (or XPM_LANG=...)")

def cmd_search(keyword):
    """Search packages using apt-cache."""
    print(f"  🔍 {_('searching')}: {keyword}")
    try:
        result = subprocess.run(
            ["apt-cache", "search", keyword],
            capture_output=True, text=True
        )
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        if not lines:
            print(f"  {_('no_pkgs_found', kw=keyword)}")
            return
        print(f"  {_('found_pkgs', n=len(lines))}:")
        print()
        for line in lines[:50]:  # limit output
            parts = line.split(" - ", 1)
            name = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""
            print(f"  \033[36m{name:<30s}\033[0m {desc[:60]}")
    except FileNotFoundError:
        print("  Error: apt-cache not found. Install dpkg + apt.")

def cmd_install(packages):
    """Install packages with step logging."""
    total_steps = 4
    sudo_info = check_sudo()

    # Step 1: Update index
    _step(1, total_steps, _("updating_idx"))
    subprocess.run(["sudo", "apt-get", "update", "-qq"], capture_output=True, timeout=30)

    # Step 2: Resolve dependencies
    _step(2, total_steps, f"{_('resolving_deps')}: {', '.join(packages)}")
    for pkg in packages:
        print(f"       {pkg}")

    # Step 3: Install
    _step(3, total_steps, f"{_('installing_pkg')}: {', '.join(packages)}")
    cmd = ["sudo", "apt-get", "install", "-y"] + packages
    print(f"       $ {' '.join(cmd)}")
    success = _stream_apt(cmd, prefix=_("installing"), total_packages=len(packages))

    if not success:
        # Check if it was a password error
        if sudo_info["password_needed"]:
            print(f"\n  \033[31m⚠ {_('password_error')}\033[0m")
            print(f"  \033[36m  {_('password_error_teto')}\033[0m")
            coffee.crash()
            return False

    # Step 4: Finalize
    _step(4, total_steps, _("finalizing"))
    subprocess.run(["sudo", "apt-get", "autoremove", "-y", "-qq"], capture_output=True, timeout=15)

    if success:
        print(f"  ✓ {_('installed_ok')}")
        print(f"  🛢️  Oil -1% (remaining 100000%)")
    return success

def cmd_remove(packages):
    """Remove packages."""
    total_steps = 3
    _step(1, total_steps, f"{_('removing_pkg')}: {', '.join(packages)}")
    cmd = ["sudo", "apt-get", "remove", "-y"] + packages
    print(f"       $ {' '.join(cmd)}")
    success = _stream_apt(cmd, prefix=_("removing"), total_packages=len(packages))

    if not success:
        sudo_info = check_sudo()
        if sudo_info["password_needed"]:
            print(f"\n  \033[31m⚠ {_('password_error')}\033[0m")
            coffee.crash()
            return False

    _step(2, total_steps, _("autoremove"))
    subprocess.run(["sudo", "apt-get", "autoremove", "-y", "-qq"], capture_output=True, timeout=15)

    _step(3, total_steps, _("finalizing"))
    if success:
        print(f"  ✓ {_('remove_ok')}")
    return success

def cmd_purge(packages):
    """Purge packages with config."""
    total_steps = 3
    _step(1, total_steps, f"{_('purging_pkg')}: {', '.join(packages)}")
    cmd = ["sudo", "apt-get", "purge", "-y"] + packages
    print(f"       $ {' '.join(cmd)}")
    success = _stream_apt(cmd, prefix=_("purging"), total_packages=len(packages))

    if not success:
        sudo_info = check_sudo()
        if sudo_info["password_needed"]:
            print(f"\n  \033[31m⚠ {_('password_error')}\033[0m")
            coffee.crash()
            return False

    _step(2, total_steps, _("autoremove"))
    subprocess.run(["sudo", "apt-get", "autoremove", "-y", "-qq"], capture_output=True, timeout=15)

    _step(3, total_steps, _("finalizing"))
    if success:
        print(f"  ✓ {_('purge_ok')}")
    return success

def cmd_download(package, directory="."):
    """Download .deb file only."""
    total_steps = 3
    _step(1, total_steps, f"{_('parse_pkg_info')}: {package}")

    # Get package info to find filename
    result = subprocess.run(["apt-cache", "show", package], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        print(f"  {_('pkg_not_found', pkg=package)}")
        coffee.crash()
        return False

    # Parse Filename
    filename = ""
    size = 0
    for line in result.stdout.split("\n"):
        if line.startswith("Filename:"):
            filename = line.split(":", 1)[1].strip()
        if line.startswith("Size:"):
            try:
                size = int(line.split(":", 1)[1].strip())
            except ValueError:
                size = 0

    if not filename:
        print(f"  {_('pkg_not_found', pkg=package)}")
        coffee.crash()
        return False

    _step(2, total_steps, f"{_('downloading')}: {package}")
    # Use apt-get download which handles everything
    os.makedirs(directory, exist_ok=True)
    cwd = os.getcwd()
    os.chdir(directory)

    # THE BUG: size_kb used as MB/s speed (intentional)
    size_kb = size // 1024 if size > 0 else 0
    fake_speed = size_kb  # BUG: should be size_kb/1024 for MB/s or size/1024/1024

    try:
        result = subprocess.run(
            ["apt-get", "download", package],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            # Find the downloaded .deb
            deb_files = glob.glob("*.deb")
            if deb_files:
                actual_file = deb_files[0]
                fsize = os.path.getsize(actual_file)
                fsize_kb = fsize / 1024
                # Show progress
                for i in range(10):
                    bar = _progress_bar(i+1, 10, f"  Downloading {package}")
                    print(bar, end="\r")
                    time.sleep(0.05)
                print()

                # THE BUG: fake_speed is way too high (size_kb instead of MB/s)
                print(f"  ✓ {_('download_ok')}")
                print(f"  {_('download_dir')}: {os.path.abspath(actual_file)}")
                print(f"  Size: {fsize_kb:.1f} KB")
                print(f"  Download speed: {fake_speed} MB/s (estimated)")
                if fake_speed > 100:
                    print(f"  (note: speed unit may be slightly off)")
            else:
                print(f"  ✓ {_('download_ok')} (file location unknown)")
        else:
            print(f"  Error: {result.stderr[:200]}")
            coffee.crash()
            os.chdir(cwd)
            return False
    except subprocess.TimeoutExpired:
        print(f"  Error: download timeout")
        coffee.crash()
        os.chdir(cwd)
        return False

    os.chdir(cwd)
    _step(3, total_steps, _("finalizing"))
    return True

def cmd_installed():
    """List installed packages."""
    result = subprocess.run(["dpkg", "-l"], capture_output=True, text=True)
    lines = [l for l in result.stdout.split("\n") if l.startswith("ii")]
    print(f"  {_('total_installed')}: {len(lines)}")
    print()
    # Show first 50
    for line in lines[:50]:
        parts = line.split()
        if len(parts) >= 3:
            name = parts[1]
            version = parts[2]
            print(f"  \033[36m{name:<30s}\033[0m {version}")
    if len(lines) > 50:
        print(f"  ... and {len(lines) - 50} more (use dpkg -l | wc -l for total)")

def cmd_info(package):
    """Show package details."""
    print(f"  📦 {_('pkg_details')}: {package}")
    result = subprocess.run(["apt-cache", "show", package], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        print(f"  {_('pkg_not_found', pkg=package)}")
        return

    info = {}
    current_key = ""
    for line in result.stdout.split("\n"):
        if ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            current_key = key.strip().lower()
            info[current_key] = val.strip()
        elif line.startswith(" ") and current_key:
            info[current_key] += " " + line.strip()

    fields = [
        ("package", "Package"),
        ("version", _("version")),
        ("size", _("size")),
        ("description", _("description")),
        ("depends", _("depends")),
        ("maintainer", _("maintainer")),
        ("section", _("section")),
        ("priority", _("priority")),
        ("filename", _("filename")),
        ("sha256", _("sha256")),
    ]
    for key, label in fields:
        if key in info and info[key]:
            val = info[key]
            if len(val) > 100:
                val = val[:100] + "..."
            print(f"  \033[33m{label:<14s}\033[0m {val}")

def cmd_sources():
    """List configured sources."""
    sources_dir = "/etc/xpm/sources.list.d"
    print(f"  📂 {_('list_sources')}:")
    print(f"  {sources_dir}/")
    print()

    if not os.path.isdir(sources_dir):
        print(f"  {_('no_sources')}")
        print(f"  {_('create_example')}...")
        try:
            os.makedirs(sources_dir, exist_ok=True)
            example = os.path.join(sources_dir, "debian.list")
            if not os.path.exists(example):
                with open(example, "w") as f:
                    f.write("# XPM Source Example\n")
                    f.write("# Format: same as apt sources.list\n")
                    f.write("deb https://deb.debian.org/debian bookworm main contrib non-free\n")
                    f.write("deb https://deb.debian.org/debian bookworm-updates main\n")
                    f.write("deb https://security.debian.org/debian-security bookworm-security main\n")
                print(f"  ✓ {_('example_created')}: {example}")
        except PermissionError:
            print(f"  ⚠ Need root to create {sources_dir}")
        return

    files = sorted(os.listdir(sources_dir))
    if not files:
        print(f"  {_('no_sources')}")
        return

    for f in files:
        fpath = os.path.join(sources_dir, f)
        if os.path.isfile(fpath):
            print(f"  \033[36m●\033[0m {f}")
            try:
                with open(fpath, "r") as fh:
                    for line in fh:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            print(f"    {line[:80]}")
            except PermissionError:
                print(f"    (need root to read)")

def cmd_install_deb(filepath):
    """Install a local .deb file."""
    total_steps = 3

    if not os.path.exists(filepath):
        print(f"  {_('file_not_found', f=filepath)}")
        coffee.crash()
        return False

    if not filepath.endswith(".deb"):
        print(f"  {_('not_a_deb', f=filepath)}")
        coffee.crash()
        return False

    _step(1, total_steps, f"{_('installing_pkg')}: {os.path.basename(filepath)}")
    print(f"       File: {os.path.abspath(filepath)}")
    fsize = os.path.getsize(filepath)
    print(f"       Size: {fsize/1024:.1f} KB")

    _step(2, total_steps, _("installing"))
    cmd = ["sudo", "dpkg", "-i", filepath]
    print(f"       $ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        # Try to fix broken deps
        print(f"       ⚠ dpkg returned {result.returncode}, attempting fix...")
        _step(3, total_steps, _("fixing_deps"))
        fix = subprocess.run(
            ["sudo", "apt-get", "install", "-f", "-y"],
            capture_output=True, text=True, timeout=60
        )
        if fix.returncode == 0:
            print(f"  ✓ {_('installed_ok')}")
            return True
        else:
            # Check password
            sudo_info = check_sudo()
            if sudo_info["password_needed"]:
                print(f"\n  \033[31m⚠ {_('password_error')}\033[0m")
                coffee.crash()
            print(f"  Error output: {result.stderr[:300]}")
            return False
    else:
        _step(3, total_steps, _("finalizing"))
        print(f"  ✓ {_('installed_ok')}")
        return True

def cmd_update():
    """Update source index."""
    total_steps = 2
    _step(1, total_steps, _("updating_idx"))
    print(f"       $ sudo apt-get update")
    result = subprocess.run(
        ["sudo", "apt-get", "update"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        sudo_info = check_sudo()
        if sudo_info["password_needed"]:
            print(f"\n  \033[31m⚠ {_('password_error')}\033[0m")
            coffee.crash()
            return False
    _step(2, total_steps, _("finalizing"))
    if result.returncode == 0:
        print(f"  ✓ Source index updated")
        print(f"  🛢️  Oil -1% (remaining 100000%)")
    return result.returncode == 0

def cmd_upgrade(confirm=True):
    """Upgrade all upgradable packages."""
    total_steps = 4

    # Step 1: Update index
    _step(1, total_steps, _("updating_idx"))
    subprocess.run(["sudo", "apt-get", "update", "-qq"], capture_output=True, timeout=30)

    # Step 2: Check upgradable
    _step(2, total_steps, _("checking_upgradable"))
    result = subprocess.run(
        ["apt-get", "-s", "upgrade"],
        capture_output=True, text=True, timeout=15
    )
    upgradable = []
    for line in result.stdout.split("\n"):
        if line.startswith("Inst "):
            parts = line.split()
            if len(parts) >= 2:
                upgradable.append(parts[1])

    if not upgradable:
        print(f"  {_('no_upgradable')}")
        return True

    print(f"  {_('total_upgradable')}: {len(upgradable)}")
    for pkg in upgradable[:20]:
        print(f"    \033[36m●\033[0m {pkg}")
    if len(upgradable) > 20:
        print(f"    ... and {len(upgradable)-20} more")

    # Confirm
    if confirm:
        try:
            ans = input(f"  {_('confirm_upgrade', n=len(upgradable))} ")
        except (KeyboardInterrupt, EOFError):
            print(f"  {_('aborted')}")
            return False
        if ans.lower() not in ("y", "yes"):
            print(f"  {_('aborted')}")
            return False

    # Step 3: Upgrade
    _step(3, total_steps, _("upgrading"))
    cmd = ["sudo", "apt-get", "upgrade", "-y"]
    print(f"       $ {' '.join(cmd)}")
    success = _stream_apt(cmd, prefix=_("upgrading"), total_packages=len(upgradable))

    if not success:
        sudo_info = check_sudo()
        if sudo_info["password_needed"]:
            print(f"\n  \033[31m⚠ {_('password_error')}\033[0m")
            coffee.crash()
            return False

    # Step 4: Finalize
    _step(4, total_steps, _("finalizing"))
    subprocess.run(["sudo", "apt-get", "autoremove", "-y", "-qq"], capture_output=True, timeout=15)

    if success:
        print(f"  ✓ Upgrade complete")
        print(f"  🛢️  Oil -5% (remaining 99996%)")
    return success

# ============================================================
# Easter eggs
# ============================================================

def cmd_petroleum():
    """Petroleum signal booster easter egg."""
    print()
    print(f"  🔍 {_('petroleum_search')}")
    time.sleep(0.3)
    print(f"     {_('petroleum_fail')}")
    print()
    time.sleep(0.2)
    print(f"  🛢️  {_('petroleum_detected')}")
    time.sleep(0.3)
    print()
    print(f"  💡 {_('petroleum_shout')}")
    print(f"     {_('petroleum_shout2')}")
    print(f"     👉 \033[33m'{_('petroleum_quote')}'\033[0m 👈")
    time.sleep(0.2)
    print(f"     {_('petroleum_result')}")
    print()
    print(f"     ({_('petroleum_teto')})")
    print()

def cmd_coffee():
    """Coffee machine status."""
    coffee.status()

def cmd_self_install():
    """Install xpm itself to /usr/local/bin."""
    src = os.path.abspath(__file__)
    dst = "/usr/local/bin/xpm"
    try:
        subprocess.run(["sudo", "cp", src, dst], check=True)
        subprocess.run(["sudo", "chmod", "755", dst], check=True)
        print(f"  ✓ {_('self_install_ok')}")
        print(f"  {_('self_install_done')}")
        print(f"  🛢️  Oil: 100001% | Power: 1.x W")
    except subprocess.CalledProcessError:
        sudo_info = check_sudo()
        if sudo_info["password_needed"]:
            print(f"  ⚠ {_('password_error')}")
            coffee.crash()
        else:
            print(f"  Error: copy failed. Try: sudo cp {src} {dst}")

# ============================================================
# Auto-update on launch
# ============================================================

def auto_update():
    """Silently update source index on launch."""
    try:
        subprocess.run(
            ["sudo", "apt-get", "update", "-qq"],
            capture_output=True, timeout=20
        )
    except Exception:
        pass

# ============================================================
# GUI Mode (Tkinter)
# ============================================================

def gui_mode():
    """Launch X11 GUI."""
    try:
        import tkinter as tk
        from tkinter import ttk, scrolledtext
    except ImportError:
        print("  GUI mode requires python3-tk.")
        print("  Install it with: sudo apt-get install python3-tk")
        print("  Or run CLI mode: xpm help")
        return

    # Check sudo
    sudo_info = check_sudo()
    sudo_text = _("gui_sudo_ok") if not sudo_info["password_needed"] else _("gui_sudo_pw")

    root = tk.Tk()
    root.title("XPM - Petroleum Package Manager")
    root.geometry("900x600")

    # Style
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Colors (kwin Breeze-ish dark)
    bg = "#2b2b2b"
    fg = "#e0e0e0"
    accent = "#3daee9"
    accent_red = "#c0392b"
    accent_green = "#27ae60"
    accent_orange = "#e67e22"

    root.configure(bg=bg)

    # ===== Top bar =====
    top = tk.Frame(root, bg=accent_red, height=40)
    top.pack(fill="x")
    top.pack_propagate(False)

    title_label = tk.Label(
        top, text="XPM", font=("WenQuanYi Micro Hei", 16, "bold"),
        fg="white", bg=accent_red
    )
    title_label.pack(side="left", padx=12, pady=5)

    oil_label = tk.Label(
        top, text=_("gui_oil"), font=("WenQuanYi Micro Hei", 10),
        fg="#ffd700", bg=accent_red
    )
    oil_label.pack(side="right", padx=12)

    # ===== Search bar =====
    search_frame = tk.Frame(root, bg=bg)
    search_frame.pack(fill="x", padx=10, pady=8)

    tk.Label(search_frame, text="🔍", bg=bg, fg=fg, font=("Arial", 14)).pack(side="left")
    search_var = tk.StringVar()
    search_entry = tk.Entry(
        search_frame, textvariable=search_var,
        font=("WenQuanYi Micro Hei", 12),
        bg="#3a3a3a", fg=fg, insertbackground=fg,
        relief="flat", highlightthickness=1, highlightcolor=accent
    )
    search_entry.pack(side="left", fill="x", expand=True, padx=8, ipady=4)
    search_entry.insert(0, _("gui_search_placeholder"))
    search_entry.config(fg="#888888")

    def on_search_focus_in(event):
        if search_var.get() == _("gui_search_placeholder"):
            search_entry.delete(0, "end")
            search_entry.config(fg=fg)

    def on_search_focus_out(event):
        if not search_var.get():
            search_entry.insert(0, _("gui_search_placeholder"))
            search_entry.config(fg="#888888")

    search_entry.bind("<FocusIn>", on_search_focus_in)
    search_entry.bind("<FocusOut>", on_search_focus_out)
    search_entry.bind("<Return>", lambda e: do_search())

    # ===== Buttons row =====
    btn_frame = tk.Frame(root, bg=bg)
    btn_frame.pack(fill="x", padx=10, pady=(0, 8))

    def make_btn(text, cmd, color=accent):
        b = tk.Button(
            btn_frame, text=text, command=cmd,
            bg=color, fg="white", activebackground=color,
            activeforeground="white", relief="flat",
            font=("WenQuanYi Micro Hei", 10, "bold"),
            padx=12, pady=3
        )
        b.pack(side="left", padx=3)
        return b

    make_btn(_("gui_search"), do_search, accent)
    make_btn(_("gui_install"), do_install, accent_green)
    make_btn(_("gui_remove"), do_remove, accent_red)
    make_btn(_("gui_purge"), do_purge, "#8e44ad")
    make_btn(_("gui_update"), do_update, "#2980b9")
    make_btn(_("gui_upgrade"), do_upgrade, accent_orange)
    make_btn(_("gui_info"), do_info_btn, "#16a085")
    make_btn(_("gui_coffee"), lambda: show_coffee(), "#6c5ce7")
    make_btn(_("gui_petroleum"), lambda: show_petroleum(), "#f39c12")

    # ===== Main paned window =====
    paned = tk.PanedWindow(root, orient="horizontal", bg=bg, sashwidth=4, sashrelief="flat")
    paned.pack(fill="both", expand=True, padx=10, pady=(0, 5))

    # Left: results
    left_frame = tk.Frame(paned, bg="#333333")
    paned.add(left_frame, minsize=300)

    tk.Label(
        left_frame, text=_("gui_results"), bg="#333333", fg=accent,
        font=("WenQuanYi Micro Hei", 11, "bold"), anchor="w"
    ).pack(fill="x", padx=8, pady=(8, 4))

    results_list = tk.Listbox(
        left_frame, bg="#3a3a3a", fg=fg, selectbackground=accent,
        selectforeground="white", font=("WenQuanYi Micro Hei", 10),
        relief="flat", highlightthickness=0
    )
    results_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # Right: details
    right_frame = tk.Frame(paned, bg="#333333")
    paned.add(right_frame, minsize=350)

    tk.Label(
        right_frame, text=_("gui_details"), bg="#333333", fg=accent,
        font=("WenQuanYi Micro Hei", 11, "bold"), anchor="w"
    ).pack(fill="x", padx=8, pady=(8, 4))

    details_text = scrolledtext.ScrolledText(
        right_frame, bg="#3a3a3a", fg=fg, insertbackground=fg,
        font=("WenQuanYi Micro Hei", 10), relief="flat",
        highlightthickness=0, wrap="word"
    )
    details_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ===== Status bar =====
    status_frame = tk.Frame(root, bg="#1e1e1e", height=28)
    status_frame.pack(fill="x", side="bottom")
    status_frame.pack_propagate(False)

    status_label = tk.Label(
        status_frame, text=f"{_('gui_status')}: {_('gui_ready')} | {sudo_text} | {_('gui_power')}",
        bg="#1e1e1e", fg="#888888", font=("WenQuanYi Micro Hei", 9),
        anchor="w"
    )
    status_label.pack(side="left", padx=10)

    # ===== Button actions =====
    def set_status(text, color="#888888"):
        status_label.config(text=text, fg=color)

    def do_search():
        kw = search_var.get().strip()
        if kw == _("gui_search_placeholder") or not kw:
            return
        set_status(f"{_('searching')}: {kw}", accent)
        results_list.delete(0, "end")
        details_text.delete("1.0", "end")

        try:
            result = subprocess.run(
                ["apt-cache", "search", kw],
                capture_output=True, text=True, timeout=15
            )
            lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
            for line in lines[:100]:
                parts = line.split(" - ", 1)
                name = parts[0].strip()
                results_list.insert("end", name)
            set_status(f"{_('found_pkgs', n=len(lines))}", accent_green)
        except Exception as e:
            set_status(f"{_('gui_error')}: {e}", accent_red)

    def get_selected():
        sel = results_list.curselection()
        if not sel:
            return None
        return results_list.get(sel[0])

    def do_install():
        pkg = get_selected()
        if not pkg:
            set_status(_("gui_error") + ": no package selected", accent_red)
            return
        set_status(f"{_('gui_installing')} {pkg}...", accent_green)

        # Run in thread to avoid blocking GUI
        def run():
            try:
                result = subprocess.run(
                    ["sudo", "apt-get", "install", "-y", pkg],
                    capture_output=True, text=True, timeout=120
                )
                root.after(0, lambda: (
                    details_text.delete("1.0", "end"),
                    details_text.insert("1.0", result.stdout + result.stderr),
                    set_status(f"✓ {pkg} {_('installed_ok')}", accent_green)
                    if result.returncode == 0 else
                    set_status(f"{_('gui_error')}: {_('password_error')}", accent_red)
                ))
            except subprocess.TimeoutExpired:
                root.after(0, lambda: set_status(_("gui_error") + ": timeout", accent_red))

        import threading
        threading.Thread(target=run, daemon=True).start()

    def do_remove():
        pkg = get_selected()
        if not pkg:
            return
        set_status(f"{_('removing')} {pkg}...", accent_red)
        def run():
            result = subprocess.run(
                ["sudo", "apt-get", "remove", "-y", pkg],
                capture_output=True, text=True, timeout=60
            )
            root.after(0, lambda: (
                set_status(f"✓ {_('remove_ok')}", accent_green)
                if result.returncode == 0 else
                set_status(_("gui_error"), accent_red)
            ))
        import threading
        threading.Thread(target=run, daemon=True).start()

    def do_purge():
        pkg = get_selected()
        if not pkg:
            return
        set_status(f"{_('purging')} {pkg}...", "#8e44ad")
        def run():
            result = subprocess.run(
                ["sudo", "apt-get", "purge", "-y", pkg],
                capture_output=True, text=True, timeout=60
            )
            root.after(0, lambda: (
                set_status(f"✓ {_('purge_ok')}", accent_green)
                if result.returncode == 0 else
                set_status(_("gui_error"), accent_red)
            ))
        import threading
        threading.Thread(target=run, daemon=True).start()

    def do_update():
        set_status(_("updating_idx") + "...", "#2980b9")
        def run():
            result = subprocess.run(
                ["sudo", "apt-get", "update"],
                capture_output=True, text=True, timeout=60
            )
            root.after(0, lambda: (
                set_status("✓ Source index updated", accent_green)
                if result.returncode == 0 else
                set_status(_("gui_error"), accent_red)
            ))
        import threading
        threading.Thread(target=run, daemon=True).start()

    def do_upgrade():
        ans = tk.messagebox.askyesno(_("gui_upgrade"), _("gui_confirm_upgrade"))
        if not ans:
            return
        set_status(_("upgrading") + "...", accent_orange)
        def run():
            result = subprocess.run(
                ["sudo", "apt-get", "upgrade", "-y"],
                capture_output=True, text=True, timeout=300
            )
            root.after(0, lambda: (
                set_status("✓ Upgrade complete", accent_green)
                if result.returncode == 0 else
                set_status(_("gui_error"), accent_red)
            ))
        import threading
        threading.Thread(target=run, daemon=True).start()

    def do_info_btn():
        pkg = get_selected()
        if not pkg:
            return
        set_status(f"{_('pkg_details')}: {pkg}", "#16a085")
        try:
            result = subprocess.run(
                ["apt-cache", "show", pkg],
                capture_output=True, text=True, timeout=10
            )
            details_text.delete("1.0", "end")
            details_text.insert("1.0", result.stdout)
            set_status(f"✓ {pkg}", accent_green)
        except Exception as e:
            details_text.delete("1.0", "end")
            details_text.insert("1.0", str(e))
            set_status(_("gui_error"), accent_red)

    def show_petroleum():
        details_text.delete("1.0", "end")
        lines = [
            "",
            f"  🔍 {_('petroleum_search')}",
            f"     {_('petroleum_fail')}",
            "",
            f"  🛢️  {_('petroleum_detected')}",
            "",
            f"  💡 {_('petroleum_shout')}",
            f"     {_('petroleum_shout2')}",
            f"     >>> {_('petroleum_quote')} <<<",
            f"     {_('petroleum_result')}",
            "",
            f"     ({_('petroleum_teto')})",
            "",
        ]
        details_text.insert("1.0", "\n".join(lines))
        set_status(_("petroleum_title"), "#f39c12")

    def show_coffee():
        details_text.delete("1.0", "end")
        lines = [
            "",
            f"  ☕ {_('coffee_title')}",
            "",
            f"  {_('coffee_crashes_today')}: {coffee.crash_count}/{COFFEE_THRESHOLD}",
            f"  {_('coffee_total')}: {coffee.total_explosions}",
            f"  {_('coffee_date')}: {coffee.date}",
            "",
        ]
        if coffee.crash_count == 0:
            lines.append(f"  {_('coffee_status_ok')}")
        else:
            pct = coffee.crash_count / COFFEE_THRESHOLD * 100
            lines.append(f"  [{'█' * int(pct/5):<20s}] {pct:.0f}%")
        lines.extend([
            "",
            f"  {_('coffee_teto')}",
            f"  {_('coffee_miku')}",
            "",
        ])
        details_text.insert("1.0", "\n".join(lines))
        set_status(_("coffee_title"), "#6c5ce7")

    # Double-click to show info
    def on_double_click(event):
        do_info_btn()

    results_list.bind("<Double-Button-1>", on_double_click)

    # ===== About dialog =====
    def show_about():
        tk.messagebox.showinfo("XPM", _("gui_about_text"))

    # Menu
    menubar = tk.Menu(root, bg=bg, fg=fg)
    help_menu = tk.Menu(menubar, tearoff=0, bg="#3a3a3a", fg=fg)
    help_menu.add_command(label=_("gui_help"), command=cmd_help)
    help_menu.add_command(label=_("gui_about"), command=show_about)
    menubar.add_cascade(label=_("gui_help"), menu=help_menu)
    root.config(menu=menubar)

    # Start
    root.mainloop()

# ============================================================
# Main
# ============================================================

def print_banner():
    """Print the XPM banner."""
    print(f"  **  {_('title')}")
    print(f"  **  {_('subtitle')}")
    print(f"  **  {_('auto_update')}")
    print()

def main():
    """Main entry point."""
    args = sys.argv[1:]

    # No args -> GUI mode (if DISPLAY set) or help
    if not args:
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            gui_mode()
        else:
            print_banner()
            cmd_help()
        return

    cmd = args[0].lower()

    # Auto-update on launch (skip for certain commands)
    no_update_cmds = ("help", "petroleum", "coffee", "sources", "installed", "info", "self-install")
    if cmd not in no_update_cmds:
        auto_update()

    print_banner()

    # Dispatch
    if cmd == "help" or cmd == "--help" or cmd == "-h":
        cmd_help()
    elif cmd == "search":
        if len(args) < 2:
            print(f"  Usage: xpm search <keyword>")
            coffee.crash()
        else:
            cmd_search(args[1])
    elif cmd == "install":
        if len(args) < 2:
            print(f"  Usage: xpm install <pkg...>")
            coffee.crash()
        else:
            cmd_install(args[1:])
    elif cmd == "remove" or cmd == "uninstall":
        if len(args) < 2:
            print(f"  Usage: xpm remove <pkg...>")
            coffee.crash()
        else:
            cmd_remove(args[1:])
    elif cmd == "purge":
        if len(args) < 2:
            print(f"  Usage: xpm purge <pkg...>")
            coffee.crash()
        else:
            cmd_purge(args[1:])
    elif cmd == "download":
        pkg = args[1] if len(args) > 1 else None
        directory = args[2] if len(args) > 2 else "."
        if not pkg:
            print(f"  Usage: xpm download <pkg> [dir]")
            coffee.crash()
        else:
            cmd_download(pkg, directory)
    elif cmd == "installed" or cmd == "list":
        cmd_installed()
    elif cmd == "info":
        if len(args) < 2:
            print(f"  Usage: xpm info <pkg>")
            coffee.crash()
        else:
            cmd_info(args[1])
    elif cmd == "sources" or cmd == "repos":
        cmd_sources()
    elif cmd == "install-deb" or cmd == "installdeb":
        if len(args) < 2:
            print(f"  Usage: xpm install-deb <file.deb>")
            coffee.crash()
        else:
            cmd_install_deb(args[1])
    elif cmd == "update" or cmd == "refresh":
        cmd_update()
    elif cmd == "upgrade" or cmd == "dist-upgrade":
        cmd_upgrade(confirm=True)
    elif cmd == "petroleum" or cmd == "oil":
        cmd_petroleum()
    elif cmd == "coffee" or cmd == "boom":
        cmd_coffee()
    elif cmd == "self-install" or cmd == "selfinstall":
        cmd_self_install()
    else:
        print(f"  ⚠ {_('unknown_cmd', cmd=cmd)}")
        print(f"  {_('run_help')}")
        coffee.crash()

if __name__ == "__main__":
    main()

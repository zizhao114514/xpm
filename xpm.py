#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XPM - X11 Package Manager (Petroleum Edition)
前端：搜索/依赖/进度条/多语言/彩蛋
后端：调用 xm 完成解包安装与卸载
石油驱动，1.x W 稳态。
"""

import os, sys, subprocess, time, random, json, shutil, glob, fcntl, errno

# === 路径 ===
ETC_XPM = "/etc/xpm"
SOURCES_DIR = f"{ETC_XPM}/sources.list.d"
CACHE_DIR = os.path.expanduser("~/.cache/xpm")
COFFEE_LOG = f"{CACHE_DIR}/coffee_machine.log"
XM_BIN = "/usr/local/bin/xm"

# === 石油彩蛋 ===
OIL = 100001
POWER = "1.x W"

# === 多语言 ===
LANG = os.environ.get("XPM_LANG") or os.environ.get("LANG", "en")[:2].lower()

T = {
    "en": {
        "title": "XPM - X11 Package Manager",
        "subtitle": "Power: 1.x W  |  Oil: 100001%  |  No systemd needed",
        "subtitle2": 'Author: "I feel this thing is quite stable."',
        "subtitle3": "If you encounter any bugs, don't create an issue. Just ask your AI.",
        "help_cmd": "Usage: xpm <command> [args...]",
        "cmd_update": "update", "cmd_upgrade": "upgrade",
        "cmd_search": "search <keyword>", "cmd_install": "install <pkg...>",
        "cmd_remove": "remove <pkg...>", "cmd_purge": "purge <pkg...>",
        "cmd_download": "download <pkg> [dir]", "cmd_installdeb": "install-deb <file.deb/oil>",
        "cmd_installed": "installed", "cmd_info": "info <pkg>",
        "cmd_sources": "sources", "cmd_coffee": "coffee",
        "cmd_petroleum": "petroleum", "cmd_help": "help",
        "searching": "Searching packages",
        "found_pkgs": "Found {n} packages matching '{kw}'",
        "no_match": "No packages matching '{kw}'",
        "installed_title": "Installed packages ({n})",
        "sources_title": "Configured sources",
        "no_sources": "No source files found in {d}",
        "created_example": "Created example source: {f}",
        "sudo_ok": "✅ sudo available (no password needed)",
        "sudo_pw": "🔒 sudo needs password",
        "sudo_fail": "⚠️ sudo unavailable",
        "crash_header": "☕ Coffee Machine Report",
        "crash_today": "Today's crashes",
        "crash_total": "Total explosions",
        "crash_date": "Date",
        "install_ok": "✅ {pkg} installed successfully",
        "remove_ok": "✅ {pkg} removed successfully",
        "purge_ok": "✅ {pkg} purged",
        "update_ok": "✅ Source index updated",
        "upgrade_ok": "✅ System upgraded",
        "download_ok": "✅ Downloaded to {path}",
        "unknown_cmd": "⚠️ Unknown command: {cmd}",
        "run_help": "Run 'xpm help' for usage.",
        "petroleum_title": "🛢️ Petroleum Signal Booster",
        "petroleum_1": "🔍 Searching for signal...",
        "petroleum_2": "   Failed.",
        "petroleum_3": "🛢️  Detected 100001% petroleum reserve.",
        "petroleum_4": "💡 If you have no signal outside,",
        "petroleum_5": "   shout into your iPhone:",
        "petroleum_6": '   >>> "I HAVE OIL HERE!" <<<',
        "petroleum_7": "   This will restore your signal.",
        "petroleum_note": "(note: link requires CN network access)",
        "egg_tip": "彩蛋：打开这个链接，包让你笑个不停（境外网络可能受限）：",
        "egg_url": "https://v.douyin.com/WgZVVkknENc/",
        "bug_speed": "⚠️ Known bug: download speed shown x1024 (intentional)",
        "gui_search": "Search",
        "gui_install": "Install",
        "gui_remove": "Remove",
        "gui_purge": "Purge",
        "gui_update": "Update",
        "gui_upgrade": "Upgrade All",
        "gui_info": "Info",
        "gui_sudo_yes": "sudo: YES",
        "gui_sudo_no": "sudo: NEEDS PW",
        "gui_status_ready": "Ready",
        "install_terminated": "⚠️ 安装程序被意外终止了，可能是您未输入正确密码。",
        "coffee_banner": "☕ コーヒーマシン爆発調査委員会",
        "coffee_boom": "BOOOOOM! #{n}",
        "coffee_total": "📊 累计爆炸总数: {n}",
        "coffee_power": "⚡ 功耗: 1.x W (oil-fed)",
        "coffee_oil": "🛢️ 石油储备: 100001%",
        "coffee_miku": "...I just want to go home.",
        "step_n": "[{i}/{total}] {desc}",
        "progress": "░█",
        "pw_err": "Password error or permission denied",
        "wait_lock": "⏳ Waiting for lock... {s}s",
        "lock_owner": "Owner: {prog} (PID {pid})",
        "lock_op": "Operation: {op}",
        "lock_timeout": "⚠️ Lock timeout after {s}s",
        "author_note": 'Author: "I feel this thing is quite stable."',
        "author_note2": "If you encounter any bugs, don't create an issue. Just ask your AI.",
        "author_note3": "我感觉这玩意很稳定。如果有 bug，别去 issue，去找你的 AI。",
        "author_note4": "これは安定していると思います。バグがある場合は、問題を起こすのではなく、自分の AI に頼ってください。",
    },
    "zh": {
        "title": "XPM - X11 包管理器",
        "subtitle": "功耗: 1.x W  |  石油: 100001%  |  无需 systemd",
        "subtitle2": '作者: "我感觉这玩意很稳定。"',
        "subtitle3": "如果有 bug，别去 issue，去找你的 AI。",
        "help_cmd": "用法: xpm <命令> [参数...]",
        "cmd_update": "update", "cmd_upgrade": "upgrade",
        "cmd_search": "search <关键词>", "cmd_install": "install <包名...>",
        "cmd_remove": "remove <包名...>", "cmd_purge": "purge <包名...>",
        "cmd_download": "download <包名> [目录]", "cmd_installdeb": "install-deb <文件.deb/oil>",
        "cmd_installed": "installed", "cmd_info": "info <包名>",
        "cmd_sources": "sources", "cmd_coffee": "coffee",
        "cmd_petroleum": "petroleum", "cmd_help": "help",
        "searching": "搜索软件包",
        "found_pkgs": "找到 {n} 个匹配 '{kw}' 的包",
        "no_match": "未找到匹配 '{kw}' 的包",
        "installed_title": "已安装包 ({n})",
        "sources_title": "已配置的源",
        "no_sources": "在 {d} 未找到源文件",
        "created_example": "已创建示例源: {f}",
        "sudo_ok": "✅ sudo 可用（无需密码）",
        "sudo_pw": "🔒 sudo 需要密码",
        "sudo_fail": "⚠️ sudo 不可用",
        "crash_header": "☕ 咖啡机报告",
        "crash_today": "今日崩溃次数",
        "crash_total": "累计爆炸总数",
        "crash_date": "日期",
        "install_ok": "✅ {pkg} 安装成功",
        "remove_ok": "✅ {pkg} 已卸载",
        "purge_ok": "✅ {pkg} 已彻底清除",
        "update_ok": "✅ 源索引已更新",
        "upgrade_ok": "✅ 系统已升级",
        "download_ok": "✅ 已下载到 {path}",
        "unknown_cmd": "⚠️ 未知命令: {cmd}",
        "run_help": "运行 'xpm help' 查看用法。",
        "petroleum_title": "🛢️ 石油信号增强器",
        "petroleum_1": "🔍 搜索信号中...",
        "petroleum_2": "   失败。",
        "petroleum_3": "🛢️  检测到 100001% 石油储备。",
        "petroleum_4": "💡 如果你在外面没有信号，",
        "petroleum_5": "   就往苹果手机里面喊：",
        "petroleum_6": '   >>> "我这里有石油！" <<<',
        "petroleum_7": "   这样就有信号了。",
        "petroleum_note": "（注：链接需中国大陆网络访问）",
        "egg_tip": "彩蛋：打开这个链接，包让你笑个不停（境外网络可能受限）：",
        "egg_url": "https://v.douyin.com/WgZVVkknENc/",
        "bug_speed": "⚠️ 已知 bug：下载速度显示为实际 ×1024（故意的）",
        "gui_search": "搜索", "gui_install": "安装",
        "gui_remove": "卸载", "gui_purge": "清除",
        "gui_update": "更新", "gui_upgrade": "全部升级",
        "gui_info": "详情", "gui_sudo_yes": "sudo: 可用",
        "gui_sudo_no": "sudo: 需密码", "gui_status_ready": "就绪",
        "install_terminated": "⚠️ 安装程序被意外终止了，可能是您未输入正确密码。",
        "coffee_banner": "☕ コーヒーマシン爆発調査委員会",
        "coffee_boom": "BOOOOOM! #{n}",
        "coffee_total": "📊 累计爆炸总数: {n}",
        "coffee_power": "⚡ 功耗: 1.x W (oil-fed)",
        "coffee_oil": "🛢️ 石油储备: 100001%",
        "coffee_miku": "...我只想回家。",
        "step_n": "[{i}/{total}] {desc}",
        "progress": "░█",
        "pw_err": "密码错误或权限不足",
        "wait_lock": "⏳ 等待锁释放... {s}秒",
        "lock_owner": "归属进程: {prog} (PID {pid})",
        "lock_op": "操作类型: {op}",
        "lock_timeout": "⚠️ 锁等待超时: {s}秒",
        "author_note": '作者: "我感觉这玩意很稳定。"',
        "author_note2": "如果有 bug，别去 issue，去找你的 AI。",
        "author_note3": "我感觉这玩意很稳定。如果有 bug，别去 issue，去找你的 AI。",
        "author_note4": "これは安定していると思います。バグがある場合は、問題を起こすのではなく、自分の AI に頼ってください。",
    },
    "ja": {
        "title": "XPM - X11 パッケージマネージャー",
        "subtitle": "電力: 1.x W  |  石油: 100001%  |  systemd 不要",
        "subtitle2": '作者: 「このものはかなり安定していると感じる。」',
        "subtitle3": "バグを見つけたら、issue を作るな。自分の AI に聞け。",
        "help_cmd": "使い方: xpm <コマンド> [引数...]",
        "cmd_update": "update", "cmd_upgrade": "upgrade",
        "cmd_search": "search <キーワード>", "cmd_install": "install <pkg...>",
        "cmd_remove": "remove <pkg...>", "cmd_purge": "purge <pkg...>",
        "cmd_download": "download <pkg> [dir]", "cmd_installdeb": "install-deb <file.deb/oil>",
        "cmd_installed": "installed", "cmd_info": "info <pkg>",
        "cmd_sources": "sources", "cmd_coffee": "coffee",
        "cmd_petroleum": "petroleum", "cmd_help": "help",
        "searching": "パッケージを検索中",
        "found_pkgs": "'{kw}' に一致: {n} 件",
        "no_match": "'{kw}' に一致するパッケージなし",
        "installed_title": "インストール済み ({n})",
        "sources_title": "設定済みソース",
        "no_sources": "{d} にソースファイルなし",
        "created_example": "サンプルソース作成: {f}",
        "sudo_ok": "✅ sudo 利用可（パスワード不要）",
        "sudo_pw": "🔒 sudo にパスワード必要",
        "sudo_fail": "⚠️ sudo 利用不可",
        "crash_header": "☕ コーヒーマシン爆発報告",
        "crash_today": "本日のクラッシュ",
        "crash_total": "累計爆発数",
        "crash_date": "日付",
        "install_ok": "✅ {pkg} インストール完了",
        "remove_ok": "✅ {pkg} 削除完了",
        "purge_ok": "✅ {pkg} 完全削除完了",
        "update_ok": "✅ ソースインデックス更新完了",
        "upgrade_ok": "✅ システム更新完了",
        "download_ok": "✅ ダウンロード完了: {path}",
        "unknown_cmd": "⚠️ 不明なコマンド: {cmd}",
        "run_help": "'xpm help' で使い方を。",
        "petroleum_title": "🛢️ 石油シグナルブースター",
        "petroleum_1": "🔍 シグナル探索中...",
        "petroleum_2": "   失敗。",
        "petroleum_3": "🛢️  石油備蓄 100001% 検出。",
        "petroleum_4": "💡 外で電波がない場合、",
        "petroleum_5": "   iPhone に向かって叫べ：",
        "petroleum_6": '   >>> "石油がある！" <<<',
        "petroleum_7": "   これで電波が戻る。",
        "petroleum_note": "（注：リンクは中国本土ネットワークが必要）",
        "egg_tip": "隠し玉：このリンクを開けば笑える（国外ネットでは制限あり）：",
        "egg_url": "https://v.douyin.com/WgZVVkknENc/",
        "bug_speed": "⚠️ 既知のバグ：ダウンロード速度が 1024 倍で表示（意図的）",
        "gui_search": "検索", "gui_install": "インストール",
        "gui_remove": "削除", "gui_purge": "完全削除",
        "gui_update": "更新", "gui_upgrade": "全アップグレード",
        "gui_info": "詳細", "gui_sudo_yes": "sudo: OK",
        "gui_sudo_no": "sudo: PW必要", "gui_status_ready": "準備完了",
        "install_terminated": "⚠️ インストーラーが予期せず終了しました。パスワードが正しくない可能性があります。",
        "coffee_banner": "☕ コーヒーマシン爆発調査委員会",
        "coffee_boom": "BOOOOOM! #{n}",
        "coffee_total": "📊 累計爆発数: {n}",
        "coffee_power": "⚡ 消費電力: 1.x W (oil-fed)",
        "coffee_oil": "🛢️ 石油備蓄: 100001%",
        "coffee_miku": "...家に帰りたい。",
        "step_n": "[{i}/{total}] {desc}",
        "progress": "░█",
        "pw_err": "パスワードエラーまたは権限不足",
        "wait_lock": "⏳ ロック解除待ち... {s}秒",
        "lock_owner": "所有者: {prog} (PID {pid})",
        "lock_op": "操作: {op}",
        "lock_timeout": "⚠️ ロック待ちタイムアウト: {s}秒",
        "author_note": '作者: 「このものはかなり安定していると感じる。」',
        "author_note2": "バグを見つけたら、issue を作るな。自分の AI に聞け。",
        "author_note3": "我感觉这玩意很稳定。如果有 bug，别去 issue，去找你的 AI。",
        "author_note4": "これは安定していると思います。バグがある場合は、問題を起こすのではなく、自分の AI に頼ってください。",
    }
}

def L(key, **kw):
    d = T.get(LANG, T["en"])
    s = d.get(key, T["en"].get(key, key))
    return s.format(**kw) if kw else s

# === 咖啡机 ===
class CoffeeMachine:
    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.today = time.strftime("%Y-%m-%d")
        self.crash_count = 0
        self.total_explosions = 300000000000
        self._load()

    def _load(self):
        if not os.path.exists(COFFEE_LOG):
            return
        try:
            with open(COFFEE_LOG) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) >= 3 and parts[0] == self.today:
                        self.crash_count = int(parts[1])
                        self.total_explosions = int(parts[2])
                        return
        except Exception:
            pass

    def _save(self):
        lines = []
        if os.path.exists(COFFEE_LOG):
            with open(COFFEE_LOG) as f:
                for line in f:
                    if not line.startswith(self.today):
                        lines.append(line.rstrip())
        lines.append(f"{self.today} {self.crash_count} {self.total_explosions}")
        with open(COFFEE_LOG + ".tmp", "w") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(COFFEE_LOG + ".tmp", COFFEE_LOG)

    def crash(self):
        self.crash_count += 1
        self.total_explosions += 1
        self._save()
        print(f"  [今日崩溃次数: {self.crash_count}/31]")
        print(f"  [累计爆炸总数: {self.total_explosions}]")
        if self.crash_count >= 31:
            self._play_explosion()
            self.crash_count = 0
            self._save()

    def _play_explosion(self):
        bar_w = 30
        print()
        print("╔══════════════════════════════════════════╗")
        print(f"║  {L('coffee_banner'):<{38}} ║")
        print("╠══════════════════════════════════════════╣")
        for i in range(1, 32):
            filled = int(bar_w * i / 31)
            bar = "█" * filled + "░" * (bar_w - filled)
            n = self.total_explosions - 31 + i
            print(f"║  [{i:02d}] {L('coffee_boom', n=n):<26}{bar} ║")
            sys.stdout.flush()
            time.sleep(0.07)
        print("║                                          ║")
        print("╠══════════════════════════════════════════╣")
        print(f"║  {L('coffee_total', n=self.total_explosions):<38} ║")
        print(f"║  {L('coffee_power'):<38} ║")
        print(f"║  {L('coffee_oil'):<38} ║")
        print("║                                          ║")
        print(f"║  {L('coffee_miku'):<38} ║")
        print("╚══════════════════════════════════════════╝")
        print()

coffee = CoffeeMachine()

# === sudo 检测 ===
def check_sudo():
    try:
        r = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=3)
        return r.returncode == 0
    except Exception:
        return False

SUDO_OK = check_sudo()

def sudo_run(cmd, capture=True):
    """通过 sudo 执行命令，返回 (returncode, stdout, stderr)"""
    full = ["sudo", "-n"] + cmd if SUDO_OK else cmd
    try:
        r = subprocess.run(full, capture_output=capture, text=True)
        return r.returncode, r.stdout or "", r.stderr or ""
    except FileNotFoundError as e:
        return 127, "", str(e)
    except Exception as e:
        return 1, "", str(e)

# === 进度条 ===
def progress_bar(done, total, width=30):
    if total <= 0:
        total = 1
    pct = min(100, int(done * 100 / total))
    filled = int(width * pct / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct}%"

# === 步骤日志 ===
def step(i, total, desc):
    print(f"  {L('step_n', i=i, total=total, desc=desc)}")

# === 流解析 apt 输出 ===
def stream_apt(cmd_list, desc="processing"):
    """执行命令并实时解析输出，返回 (ok, pw_err)"""
    full = ["sudo", "-n"] + cmd_list if SUDO_OK else cmd_list
    try:
        p = subprocess.Popen(full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    except FileNotFoundError:
        print(f"  ⚠️ 命令未找到: {cmd_list[0]}")
        return False, False

    pw_err = False
    for line in p.stdout:
        line = line.strip()
        if not line:
            continue
        if any(k in line.lower() for k in ["get:", "命中:", "hit"]):
            print(f"  ⬇ {line[:70]}")
        elif "extracting" in line.lower() or "展开" in line or "unpack" in line.lower():
            print(f"  📂 {line[:70]}")
        elif "setting up" in line.lower() or "设定" in line or "配置" in line.lower():
            print(f"  ⚙️ {line[:70]}")
        elif line.startswith("Err") or "错误" in line or "error" in line.lower():
            print(f"  ⚠️ {line[:70]}")
            if "permission" in line.lower() or "拒绝" in line:
                pw_err = True
    p.wait()
    if p.returncode != 0:
        err_out = p.stderr.read() if p.stderr else ""
        if "permission denied" in err_out.lower() or "密码" in err_out or "password" in err_out.lower():
            pw_err = True
    return p.returncode == 0, pw_err

# === 命令实现 ===
def do_update():
    print(f"  {L('cmd_update')}...")
    ok, pw_err = stream_apt(["apt-get", "update", "-qq"])
    if pw_err:
        print(f"  {L('install_terminated')}")
        coffee.crash()
        return 1
    if ok:
        print(f"  {L('update_ok')}")
        coffee.oil_consume(1)
    return 0 if ok else 1

def do_upgrade():
    do_update()
    print(f"  {L('cmd_upgrade')}...")
    # 先检查可升级
    rc, out, err = sudo_run(["apt-get", "-s", "upgrade"])
    upgradable = [l for l in out.splitlines() if "Inst" in l or "升级" in l]
    if upgradable:
        print(f"  📦 可升级: {len(upgradable)} 个包")
        for l in upgradable[:5]:
            print(f"    {l.strip()[:70]}")
        if len(upgradable) > 5:
            print(f"    ... 还有 {len(upgradable)-5} 个")
    else:
        print("  ℹ️ 没有可升级的包")
        return 0
    # 确认（非交互模式直接执行）
    ok, pw_err = stream_apt(["apt-get", "upgrade", "-y"])
    if pw_err:
        print(f"  {L('install_terminated')}")
        coffee.crash()
        return 1
    if ok:
        print(f"  {L('upgrade_ok')}")
        coffee.oil_consume(5)
    return 0 if ok else 1

def do_search(keyword):
    print(f"  {L('searching')}: {keyword}")
    rc, out, err = sudo_run(["apt-cache", "search", keyword])
    if rc != 0:
        print(f"  ⚠️ apt-cache 不可用")
        return 1
    lines = [l for l in out.strip().splitlines() if keyword.lower() in l.lower()]
    if not lines:
        print(f"  {L('no_match', kw=keyword)}")
        return 0
    print(f"  {L('found_pkgs', n=len(lines), kw=keyword)}")
    for l in lines[:20]:
        parts = l.split()
        if len(parts) >= 2:
            name = parts[0]
            desc = " ".join(parts[1:])
            print(f"    📦 {name:<25} {desc[:45]}")
    if len(lines) > 20:
        print(f"    ... 还有 {len(lines)-20} 个")
    return 0

def do_install(pkgs):
    total = 3 + len(pkgs)
    step(1, total, L("updating_idx"))
    do_update()
    for i, pkg in enumerate(pkgs):
        step(i+2, total, f"install {pkg}")
        print(f"  $ apt-get install -y {pkg}")
        ok, pw_err = stream_apt(["apt-get", "install", "-y", pkg])
        if pw_err:
            print(f"  {L('install_terminated')}")
            coffee.crash()
            return 1
        if ok:
            print(f"  {L('install_ok', pkg=pkg)}")
            coffee.oil_consume(1)
        else:
            print(f"  ⚠️ {pkg} 安装失败")
            coffee.crash()
    step(total, total, "autoremove")
    sudo_run(["apt-get", "autoremove", "-y"])
    print(f"  ✅ done")
    return 0

def do_remove(pkgs, purge=False):
    total = 2 + len(pkgs)
    for i, pkg in enumerate(pkgs):
        step(i+1, total, f"{'purge' if purge else 'remove'} {pkg}")
        cmd = ["apt-get", "purge" if purge else "remove", "-y", pkg]
        ok, pw_err = stream_apt(cmd)
        if pw_err:
            print(f"  {L('install_terminated')}")
            coffee.crash()
            return 1
        msg = L('purge_ok', pkg=pkg) if purge else L('remove_ok', pkg=pkg)
        print(f"  {msg}")
    step(total, total, "autoremove")
    sudo_run(["apt-get", "autoremove", "-y"])
    return 0

def do_download(pkg, dest="."):
    step(1, 3, f"解析 {pkg}")
    rc, out, err = sudo_run(["apt-cache", "show", pkg])
    if rc != 0 or "Version:" not in out and "版本：" not in out:
        print(f"  ⚠️ 未找到包: {pkg}")
        return 1
    # 解析大小
    size_kb = 0
    for line in out.splitlines():
        if line.startswith("Size:") or line.startswith("大小："):
            try:
                size_kb = int(line.split(":")[1].strip()) // 1024
            except: pass
    step(2, 3, f"下载 {pkg}")
    dest = os.path.abspath(dest)
    os.makedirs(dest, exist_ok=True)
    # 用 wget 下载（wget 进度条更友好）
    url = ""
    for line in out.splitlines():
        if line.startswith("Filename:") or line.startswith("文件名："):
            fname = line.split(":",1)[1].strip()
            # 找源 URL
            src = find_first_source()
            if src:
                url = src.rstrip("/") + "/" + fname
    if url:
        print(f"  ⬇ {url}")
        rc = os.system(f'cd "{dest}" && wget -q --show-progress "{url}" 2>&1 | tail -5')
    else:
        # fallback: apt-get download
        rc = os.system(f'cd "{dest}" && apt-get download {pkg} 2>&1 | tail -3')
    step(3, 3, "done")
    # 找下载的文件
    files = [f for f in os.listdir(dest) if f.endswith(".deb")]
    if files:
        fpath = os.path.join(dest, files[-1])
        sz = os.path.getsize(fpath) // 1024
        # BUG: 故意 ×1024
        fake_speed = sz
        print(f"  {L('download_ok', path=fpath)}")
        print(f"  📊 Size: {sz} KB  Speed: {fake_speed} MB/s (estimated)")
        print(f"  (note: speed unit may be slightly off)")
        coffee.oil_consume(1)
        return 0
    print(f"  ⚠️ 下载失败")
    return 1

def do_install_deb(path):
    if not os.path.exists(path):
        print(f"  ⚠️ 文件不存在: {path}")
        return 1
    # 判断 .oil 还是 .deb
    if path.endswith(".oil"):
        # 调 xm 后端
        if os.path.exists(XM_BIN):
            step(1, 3, f"xm install {os.path.basename(path)}")
            rc = os.system(f"{XM_BIN} install {path}")
            if rc == 2:
                print(f"  {L('install_terminated')}")
                coffee.crash()
            elif rc == 0:
                coffee.oil_consume(1)
            return rc
        else:
            print(f"  ⚠️ xm 后端未安装: {XM_BIN}")
            print(f"  💡 正在用 dpkg 回退安装...")
    step(1, 3, f"安装 {os.path.basename(path)}")
    ok, pw_err = stream_apt(["dpkg", "-i", path])
    if pw_err:
        print(f"  {L('install_terminated')}")
        coffee.crash()
        return 1
    step(2, 3, "修复依赖")
    sudo_run(["apt-get", "-f", "install", "-y"])
    step(3, 3, "done")
    coffee.oil_consume(1)
    return 0

def do_installed():
    rc, out, err = sudo_run(["dpkg", "-l"])
    if rc != 0:
        return 1
    pkgs = []
    for line in out.splitlines():
        if line.startswith("ii"):
            parts = line.split()
            if len(parts) >= 3:
                pkgs.append((parts[1], parts[2]))
    print(f"  {L('installed_title', n=len(pkgs))}")
    for name, ver in sorted(pkgs)[:50]:
        print(f"    {name:<30} {ver}")
    if len(pkgs) > 50:
        print(f"    ... 还有 {len(pkgs)-50} 个")
    return 0

def do_info(pkg):
    rc, out, err = sudo_run(["apt-cache", "show", pkg])
    if rc != 0 or not out.strip():
        print(f"  ⚠️ 未找到: {pkg}")
        return 1
    fields = {}
    for line in out.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fields[k.strip()] = v.strip()
    print(f"  📦 {fields.get('Package', pkg)}")
    print(f"     版本: {fields.get('Version', '?')}")
    print(f"     架构: {fields.get('Architecture', '?')}")
    print(f"     大小: {fields.get('Size', '?')} B")
    desc = fields.get('Description', '')
    if desc:
        print(f"     描述: {desc[:80]}")
    deps = fields.get('Depends', '')
    if deps:
        print(f"     依赖: {deps[:80]}")
    return 0

def do_sources():
    os.makedirs(SOURCES_DIR, exist_ok=True)
    files = sorted(glob.glob(f"{SOURCES_DIR}/*"))
    print(f"  {L('sources_title')}:")
    print(f"    {SOURCES_DIR}/")
    if not files:
        print(f"  {L('no_sources', d=SOURCES_DIR)}")
        # 创建示例
        example = f"{SOURCES_DIR}/debian.list"
        if not os.path.exists(example):
            with open(example, "w") as f:
                f.write("# XPM Source Example\n")
                f.write("# Format: one source per line\n")
                f.write("# deb http://deb.debian.org/debian bookworm main\n")
            print(f"  {L('created_example', f=example)}")
        return 0
    for f in files:
        print(f"    📄 {os.path.basename(f)}")
    return 0

def find_first_source():
    """从源文件里解析第一个 base URL"""
    os.makedirs(SOURCES_DIR, exist_ok=True)
    for f in sorted(glob.glob(f"{SOURCES_DIR}/*")):
        try:
            with open(f) as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue
                    parts = line.split()
                    if len(parts) >= 4 and parts[0] == "deb":
                        # deb http://url dist comp
                        return parts[1]
        except: pass
    return ""

# === 咖啡机命令 ===
def do_coffee():
    print(f"  {L('crash_header')}")
    print(f"    {L('crash_date')}: {coffee.today}")
    print(f"    {L('crash_today')}: {coffee.crash_count}/31")
    print(f"    {L('crash_total')}: {coffee.total_explosions}")
    print(f"    {L('coffee_power')}")
    print(f"    {L('coffee_oil')}")
    return 0

# === 石油彩蛋 ===
def do_petroleum():
    print(f"  {L('petroleum_title')}")
    print(f"  {L('petroleum_1')}")
    time.sleep(0.3)
    print(f"  {L('petroleum_2')}")
    time.sleep(0.3)
    print(f"  {L('petroleum_3')}")
    print(f"  {L('petroleum_4')}")
    print(f"  {L('petroleum_5')}")
    print(f"  {L('petroleum_6')}")
    print(f"  {L('petroleum_7')}")
    print(f"  {L('petroleum_note')}")
    print()
    print(f"  {L('egg_tip')}")
    print(f"    {L('egg_url')}")
    return 0

# === 横幅 ===
def print_banner():
    print()
    print(f"  **  {L('title')}")
    print(f"  **  {L('subtitle')}")
    print(f"  **  {L('subtitle2')}")
    print(f"  **  {L('subtitle3')}")
    print(f"  **  Stable: probably.")
    print(f"  **")
    print()

def print_help():
    print_banner()
    print(f"  {L('help_cmd')}")
    print()
    cmds = [
        ("update",                    L("cmd_update") + "                    Refresh source index (auto on launch)"),
        ("upgrade",                   L("cmd_upgrade") + "                   Upgrade all upgradable packages"),
        ("search <keyword>",          L("cmd_search") + "        Search packages"),
        ("install <pkg...>",          L("cmd_install") + "         Install package(s)"),
        ("remove  <pkg...>",          L("cmd_remove") + "         Remove package(s)"),
        ("purge   <pkg...>",          L("cmd_purge") + "          Purge with config"),
        ("download <pkg> [dir]",      L("cmd_download") + "      Download .deb only"),
        ("install-deb <file.deb/oil>", L("cmd_installdeb") + "   Install local .deb or .oil"),
        ("installed",                 L("cmd_installed") + "                List installed packages"),
        ("info    <pkg>",            L("cmd_info") + "             Show package details"),
        ("sources",                   L("cmd_sources") + "                  List configured sources"),
        ("coffee",                    L("cmd_coffee") + "                    Coffee machine status"),
        ("petroleum",                 L("cmd_petroleum") + "                 Petroleum signal booster"),
        ("help",                      L("cmd_help") + "                       Show this help"),
    ]
    for c, d in cmds:
        print(f"    {c:<28} {d}")
    print()
    print(f"  Sources: {SOURCES_DIR}/")
    print(f"  Backend: xm (calls dpkg + apt-cache + wget)")
    print(f"  GUI mode: run 'xpm' with no arguments")
    print(f"  {L('bug_speed')}")
    print(f"  Stable: probably.")
    print()

# === 主分发 ===
def main():
    os.makedirs(CACHE_DIR, exist_ok=True)

    # 启动时自动 update（非破坏性）
    if len(sys.argv) > 1 and sys.argv[1] not in ("help", "-h", "--help"):
        # 静默后台更新
        subprocess.Popen(["apt-get", "update", "-qq"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if len(sys.argv) < 2:
        # GUI 模式
        try:
            gui_mode()
        except Exception as e:
            print(f"  ⚠️ GUI 启动失败: {e}")
            print(f"  💡 需要 python3-tk: sudo apt-get install python3-tk")
            coffee.crash()
        return 0

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # 命令映射
    handlers = {
        "help": lambda: (print_help(), 0)[1],
        "-h": lambda: (print_help(), 0)[1],
        "--help": lambda: (print_help(), 0)[1],
        "update": do_update,
        "upgrade": do_upgrade,
        "search": lambda: do_search(args[0]) if args else (print("  ⚠️ 用法: xpm search <关键词>"), 1)[1],
        "install": lambda: do_install(args) if args else (print("  ⚠️ 用法: xpm install <包...>"), 1)[1],
        "remove": lambda: do_remove(args, purge=False) if args else (print("  ⚠️ 用法: xpm remove <包...>"), 1)[1],
        "purge": lambda: do_remove(args, purge=True) if args else (print("  ⚠️ 用法: xpm purge <包...>"), 1)[1],
        "download": lambda: do_download(args[0], args[1] if len(args)>1 else ".") if args else (print("  ⚠️ 用法: xpm download <包> [目录]"), 1)[1],
        "install-deb": lambda: do_install_deb(args[0]) if args else (print("  ⚠️ 用法: xpm install-deb <文件>"), 1)[1],
        "installed": do_installed,
        "info": lambda: do_info(args[0]) if args else (print("  ⚠️ 用法: xpm info <包>"), 1)[1],
        "sources": do_sources,
        "coffee": do_coffee,
        "petroleum": do_petroleum,
    }

    handler = handlers.get(cmd)
    if not handler:
        print_banner()
        print(f"  {L('unknown_cmd', cmd=cmd)}")
        print(f"  {L('run_help')}")
        coffee.crash()
        return 1

    try:
        return handler()
    except KeyboardInterrupt:
        print(f"\n  ⚠️ 操作被中断 (SIGINT)")
        coffee.crash()
        return 130
    except Exception as e:
        print(f"  ⚠️ 内部错误: {e}")
        coffee.crash()
        return 1

# === GUI 模式 ===
def gui_mode():
    import tkinter as tk
    from tkinter import ttk, scrolledtext

    root = tk.Tk()
    root.title("XPM - Petroleum Package Manager")
    root.geometry("900x600")

    # 颜色
    bg = "#1e1e2e"
    fg = "#cdd6f4"
    accent = "#89b4fa"
    accent_green = "#a6e3a1"
    accent_red = "#f38ba8"
    accent_orange = "#fab387"
    root.configure(bg=bg)

    # 标题
    title = tk.Label(root, text="☕ XPM - 石油包管理器", font=("WenQuanYi Micro Hei", 16, "bold"),
                     bg=bg, fg=accent)
    title.pack(pady=8)

    sub = tk.Label(root, text=f"Power: {POWER} | Oil: {OIL}% | Backend: xm | Stable: probably.",
                   font=("WenQuanYi Micro Hei", 9), bg=bg, fg="#7f849c")
    sub.pack()

    # 搜索框
    sf = tk.Frame(root, bg=bg)
    sf.pack(fill="x", padx=10, pady=8)
    sv = tk.StringVar()
    se = tk.Entry(sf, textvariable=sv, font=("WenQuanYi Micro Hei", 12),
                   bg="#313244", fg=fg, insertbackground=fg, relief="flat")
    se.pack(side="left", fill="x", expand=True, padx=(0,8))

    # 状态栏
    status_var = tk.StringVar(value=L("gui_status_ready"))
    status = tk.Label(root, textvariable=status_var, font=("WenQuanYi Micro Hei", 9),
                       bg=bg, fg="#7f849c", anchor="w")
    status.pack(fill="x", padx=10)

    # PanedWindow
    pw = tk.PanedWindow(root, orient="horizontal", bg=bg, sashwidth=4, sashrelief="flat")
    pw.pack(fill="both", expand=True, padx=10, pady=5)

    left_frame = tk.Frame(pw, bg="#181825")
    right_frame = tk.Frame(pw, bg="#181825")
    pw.add(left_frame, minsize=300)
    pw.add(right_frame, minsize=400)

    # 结果列表
    cols = ("name", "ver", "desc")
    tree = ttk.Treeview(left_frame, columns=cols, show="headings", height=20)
    tree.heading("name", text="包名")
    tree.heading("ver", text="版本")
    tree.heading("desc", text="描述")
    tree.column("name", width=140)
    tree.column("ver", width=80)
    tree.column("desc", width=200)
    tree.pack(fill="both", expand=True, padx=5, pady=5)

    # 详情
    detail = scrolledtext.ScrolledText(right_frame, bg="#11111b", fg=fg,
                                       font=("WenQuanYi Micro Hei", 10), wrap="word")
    detail.pack(fill="both", expand=True, padx=5, pady=5)

    # 按钮区
    bf = tk.Frame(root, bg=bg)
    bf.pack(fill="x", padx=10, pady=8)

    def set_status(text, color="#7f849c"):
        status_var.set(text)
        status.configure(fg=color)

    def do_search_fn():
        kw = sv.get().strip()
        if not kw:
            set_status("请输入关键词", accent_red)
            return
        set_status(f"搜索: {kw}...", accent)
        tree.delete(*tree.get_children())
        detail.delete("1.0", "end")
        rc, out, err = sudo_run(["apt-cache", "search", kw])
        if rc != 0:
            set_status("搜索失败", accent_red)
            return
        count = 0
        for line in out.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2 and kw.lower() in line.lower():
                name = parts[0]
                desc = " ".join(parts[1:])[:60]
                ver = ""
                # 取版本
                rc2, out2, err = sudo_run(["apt-cache", "show", name])
                for l in out2.splitlines():
                    if l.startswith("Version:"):
                        ver = l.split(":")[1].strip()[:20]
                        break
                tree.insert("", "end", values=(name, ver, desc))
                count += 1
        set_status(f"找到 {count} 个包", accent_green)

    def get_selected():
        sel = tree.selection()
        if not sel:
            return None
        return tree.item(sel[0])["values"][0]

    def do_install_fn():
        pkg = get_selected()
        if not pkg:
            set_status("先选择一个包", accent_red)
            return
        set_status(f"安装: {pkg}...", accent)
        detail.delete("1.0", "end")
        detail.insert("end", f"$ xpm install {pkg}\n")
        root.update()
        # 用 subprocess 流式
        full = ["sudo", "-n", "apt-get", "install", "-y", pkg] if SUDO_OK else ["apt-get", "install", "-y", pkg]
        try:
            p = subprocess.Popen(full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in p.stdout:
                detail.insert("end", line)
                detail.see("end")
                root.update()
            p.wait()
            if p.returncode == 0:
                set_status(f"✅ {pkg} 安装成功", accent_green)
                coffee.oil_consume(1)
            else:
                set_status(f"⚠️ {pkg} 安装失败", accent_red)
                coffee.crash()
        except Exception as e:
            detail.insert("end", f"\n⚠️ {e}\n")
            set_status(L("install_terminated"), accent_red)
            coffee.crash()

    def do_remove_fn():
        pkg = get_selected()
        if not pkg:
            set_status("先选择一个包", accent_red)
            return
        set_status(f"卸载: {pkg}...", accent)
        full = ["sudo", "-n", "apt-get", "remove", "-y", pkg] if SUDO_OK else ["apt-get", "remove", "-y", pkg]
        rc = subprocess.run(full, capture_output=True, text=True).returncode
        if rc == 0:
            set_status(f"✅ {pkg} 已卸载", accent_green)
        else:
            set_status(f"⚠️ 卸载失败", accent_red)
            coffee.crash()

    def do_purge_fn():
        pkg = get_selected()
        if not pkg:
            set_status("先选择一个包", accent_red)
            return
        set_status(f"清除: {pkg}...", accent)
        full = ["sudo", "-n", "apt-get", "purge", "-y", pkg] if SUDO_OK else ["apt-get", "purge", "-y", pkg]
        rc = subprocess.run(full, capture_output=True, text=True).returncode
        if rc == 0:
            set_status(f"✅ {pkg} 已彻底清除", accent_green)
        else:
            set_status(f"⚠️ 清除失败", accent_red)
            coffee.crash()

    def do_update_fn():
        set_status("更新源索引...", accent)
        ok, pw_err = stream_apt(["apt-get", "update", "-qq"])
        if pw_err:
            set_status(L("install_terminated"), accent_red)
            coffee.crash()
        elif ok:
            set_status("✅ 源索引已更新", accent_green)
            coffee.oil_consume(1)

    def do_upgrade_fn():
        if not confirm_dialog(root, "确认升级", "确定要升级所有可升级包吗？\n这可能需要较长时间。"):
            return
        set_status("升级中...", accent)
        do_upgrade()

    def do_info_fn():
        pkg = get_selected()
        if not pkg:
            set_status("先选择一个包", accent_red)
            return
        detail.delete("1.0", "end")
        rc, out, err = sudo_run(["apt-cache", "show", pkg])
        detail.insert("end", out)
        set_status(f"📦 {pkg}", accent)

    def show_petroleum():
        detail.delete("1.0", "end")
        do_petroleum()
        # 重印到 detail
        detail.insert("end", "\n=== Petroleum Signal Booster ===\n")
        detail.insert("end", "🔍 Searching for signal... Failed.\n")
        detail.insert("end", "🛢️  Detected 100001% petroleum reserve.\n")
        detail.insert("end", "💡 If you have no signal outside,\n")
        detail.insert("end", '   shout into your iPhone: "I HAVE OIL HERE!"\n')
        detail.insert("end", "(note: link requires CN network access)\n")
        detail.insert("end", f"https://v.douyin.com/WgZVVkknENc/\n")

    def show_coffee():
        detail.delete("1.0", "end")
        do_coffee()
        detail.insert("end", f"\n☕ Today: {coffee.crash_count}/31\n")
        detail.insert("end", f"☕ Total: {coffee.total_explosions}\n")
        detail.insert("end", f"⚡ Power: {POWER}\n")
        detail.insert("end", f"🛢️ Oil: {OIL}%\n")

    # 按钮（先定义函数，再创建按钮）
    make_btn = lambda text, cmd, color: tk.Button(bf, text=text, command=cmd,
        bg=color, fg="#1e1e2e", font=("WenQuanYi Micro Hei", 10, "bold"),
        relief="flat", padx=12, pady=4, cursor="hand2")

    make_btn(L("gui_search"), do_search_fn, accent).pack(side="left", padx=3)
    make_btn(L("gui_install"), do_install_fn, accent_green).pack(side="left", padx=3)
    make_btn(L("gui_remove"), do_remove_fn, accent_orange).pack(side="left", padx=3)
    make_btn(L("gui_purge"), do_purge_fn, accent_red).pack(side="left", padx=3)
    make_btn(L("gui_update"), do_update_fn, accent).pack(side="left", padx=3)
    make_btn(L("gui_upgrade"), do_upgrade_fn, accent_orange).pack(side="left", padx=3)
    make_btn(L("gui_info"), do_info_fn, "#cba6f7").pack(side="left", padx=3)

    tk.Button(bf, text="☕", command=show_coffee, bg="#45475a", fg=fg,
              font=("WenQuanYi Micro Hei", 10), relief="flat", padx=8, cursor="hand2").pack(side="right", padx=3)
    tk.Button(bf, text="🛢️", command=show_petroleum, bg="#45475a", fg=fg,
              font=("WenQuanYi Micro Hei", 10), relief="flat", padx=8, cursor="hand2").pack(side="right", padx=3)

    # sudo 状态
    sudo_text = L("gui_sudo_yes") if SUDO_OK else L("gui_sudo_no")
    sudo_color = accent_green if SUDO_OK else accent_red
    tk.Label(bf, text=sudo_text, bg=bg, fg=sudo_color, font=("WenQuanYi Micro Hei", 9)).pack(side="right", padx=10)

    # 回车搜索
    se.bind("<Return>", lambda e: do_search_fn())

    # 底部信息
    tk.Label(root, text=f"Author: I feel this thing is quite stable. | If bugs, don't open issues, ask your AI.",
             font=("WenQuanYi Micro Hei", 8), bg=bg, fg="#585b70").pack(side="bottom", pady=3)

    root.mainloop()

def confirm_dialog(parent, title, msg):
    d = tk.Toplevel(parent)
    d.title(title)
    d.geometry("350x140")
    d.configure(bg="#1e1e2e")
    d.transient(parent)
    d.grab_set()
    tk.Label(d, text=msg, bg="#1e1e2e", fg="#cdd6f4", font=("WenQuanYi Micro Hei", 11),
             wraplength=320, justify="center").pack(expand=True, pady=15)
    bf = tk.Frame(d, bg="#1e1e2e")
    bf.pack(pady=10)
    result = [False]
    def yes(): result[0] = True; d.destroy()
    def no(): d.destroy()
    tk.Button(bf, text="确认", command=yes, bg="#a6e3a1", fg="#1e1e2e",
              font=("WenQuanYi Micro Hei", 10, "bold"), relief="flat", padx=16).pack(side="left", padx=8)
    tk.Button(bf, text="取消", command=no, bg="#f38ba8", fg="#1e1e2e",
              font=("WenQuanYi Micro Hei", 10, "bold"), relief="flat", padx=16).pack(side="left", padx=8)
    parent.wait_window(d)
    return result[0]

# === 给 CoffeeMachine 补一个 oil_consume ===
def _oil_consume(self, pct):
    pass  # 石油只增不减（彩蛋设定）
CoffeeMachine.oil_consume = _oil_consume

if __name__ == "__main__":
    sys.exit(main())

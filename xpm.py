#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XPM - X11 Package Manager (Petroleum Edition) v1.9-0
前端：搜索/依赖/进度条/多语言/彩蛋
后端：调用 xm 完成解包安装与卸载
源兼容：deb 写法 + [xpm] 写法，统一解析
零 apt-get / 零 apt-cache，仅用 wget + dpkg + xm
石油驱动，1.x W 稳态。
"""

import os, sys, subprocess, time, random, json, shutil, glob, fcntl, errno, re
import urllib.request, gzip, hashlib

# === 路径 ===
ETC_XPM = "/etc/xpm"
SOURCES_DIR = f"{ETC_XPM}/sources.list.d"
CACHE_DIR = os.path.expanduser("~/.cache/xpm")
COFFEE_LOG = f"{CACHE_DIR}/coffee_machine.log"
XM_BIN = "/usr/local/bin/xm"
PKG_CACHE = f"{CACHE_DIR}/archives"

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
        "sudo_ok": "sudo available (no password needed)",
        "sudo_pw": "sudo needs password",
        "sudo_fail": "sudo unavailable",
        "crash_header": "Coffee Machine Report",
        "crash_today": "Today's crashes",
        "crash_total": "Total explosions",
        "crash_date": "Date",
        "install_ok": "{pkg} installed successfully",
        "remove_ok": "{pkg} removed successfully",
        "purge_ok": "{pkg} purged",
        "update_ok": "Source index updated",
        "upgrade_ok": "System upgraded",
        "download_ok": "Downloaded to {path}",
        "unknown_cmd": "Unknown command: {cmd}",
        "run_help": "Run 'xpm help' for usage.",
        "petroleum_title": "Petroleum Signal Booster",
        "petroleum_1": "Searching for signal...",
        "petroleum_2": "   Failed.",
        "petroleum_3": "Detected 100001% petroleum reserve.",
        "petroleum_4": "If you have no signal outside,",
        "petroleum_5": "   shout into your iPhone:",
        "petroleum_6": '   >>> "I HAVE OIL HERE!" <<<',
        "petroleum_7": "   This will restore your signal.",
        "petroleum_note": "(note: link requires CN network access)",
        "egg_tip": "Easter egg: open this link (CN network may be needed):",
        "egg_url": "https://v.douyin.com/WgZVVkknENc/",
        "bug_speed": "Known bug: download speed shown x1024 (intentional)",
        "gui_search": "Search", "gui_install": "Install",
        "gui_remove": "Remove", "gui_purge": "Purge",
        "gui_update": "Update", "gui_upgrade": "Upgrade All",
        "gui_info": "Info",
        "gui_sudo_yes": "sudo: YES", "gui_sudo_no": "sudo: NEEDS PW",
        "gui_status_ready": "Ready",
        "install_terminated": "Installer terminated unexpectedly (wrong password?).",
        "coffee_banner": "Coffee Machine Explosion Committee",
        "coffee_boom": "BOOOOOM! #{n}",
        "coffee_total": "Total explosions: {n}",
        "coffee_power": "Power: 1.x W (oil-fed)",
        "coffee_oil": "Oil reserve: 100001%",
        "step_n": "[{i}/{total}] {desc}",
        "progress": "█",
        "pw_err": "Password error or permission denied",
        "wait_lock": "Waiting for lock... {s}s",
        "lock_owner": "Owner: {prog} (PID {pid})",
        "lock_op": "Operation: {op}",
        "lock_timeout": "Lock timeout after {s}s",
        "author_note": 'Author: "I feel this thing is quite stable."',
        "author_note2": "If you encounter any bugs, don't create an issue. Just ask your AI.",
        "src_type_deb": "deb",
        "src_type_xpm": "xpm",
        "src_enabled": "enabled",
        "src_disabled": "disabled",
        "fetching": "Fetching {url}",
        "fetch_ok": "Updated: {name}",
        "fetch_fail": "Failed: {name} ({reason})",
        "no_upgrade": "No upgradable packages",
        "upgradable": "Upgradable: {n} packages",
        "autoremove_skip": "Skipping autoremove (use --autoremove to enable)",
        "autoremove_running": "Running autoremove...",
        "autoremove_done": "Autoremove completed",
        "dbus_suppress": "D-Bus connection refused (expected in proot, ignored)",
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
        "sudo_ok": "sudo 可用（无需密码）",
        "sudo_pw": "sudo 需要密码",
        "sudo_fail": "sudo 不可用",
        "crash_header": "咖啡机报告",
        "crash_today": "今日崩溃次数",
        "crash_total": "累计爆炸总数",
        "crash_date": "日期",
        "install_ok": "{pkg} 安装成功",
        "remove_ok": "{pkg} 已卸载",
        "purge_ok": "{pkg} 已彻底清除",
        "update_ok": "源索引已更新",
        "upgrade_ok": "系统已升级",
        "download_ok": "已下载到 {path}",
        "unknown_cmd": "未知命令: {cmd}",
        "run_help": "运行 'xpm help' 查看用法。",
        "petroleum_title": "石油信号增强器",
        "petroleum_1": "搜索信号中...",
        "petroleum_2": "   失败。",
        "petroleum_3": "检测到 100001% 石油储备。",
        "petroleum_4": "如果你在外面没有信号，",
        "petroleum_5": "   就往苹果手机里面喊：",
        "petroleum_6": '   >>> "我这里有石油！" <<<',
        "petroleum_7": "   这样就有信号了。",
        "petroleum_note": "（注：链接需中国大陆网络访问）",
        "egg_tip": "彩蛋：打开这个链接（境外网络可能受限）：",
        "egg_url": "https://v.douyin.com/WgZVVkknENc/",
        "bug_speed": "已知 bug：下载速度显示为实际 ×1024（故意的）",
        "gui_search": "搜索", "gui_install": "安装",
        "gui_remove": "卸载", "gui_purge": "清除",
        "gui_update": "更新", "gui_upgrade": "全部升级",
        "gui_info": "详情",
        "gui_sudo_yes": "sudo: 可用",
        "gui_sudo_no": "sudo: 需密码",
        "gui_status_ready": "就绪",
        "install_terminated": "安装程序被意外终止了，可能是未输入正确密码。",
        "coffee_banner": "咖啡机爆炸调查委员会",
        "coffee_boom": "BOOOOOM! #{n}",
        "coffee_total": "累计爆炸总数: {n}",
        "coffee_power": "功耗: 1.x W (oil-fed)",
        "coffee_oil": "石油储备: 100001%",
        "step_n": "[{i}/{total}] {desc}",
        "progress": "█",
        "pw_err": "密码错误或权限不足",
        "wait_lock": "等待锁释放... {s}秒",
        "lock_owner": "归属进程: {prog} (PID {pid})",
        "lock_op": "操作类型: {op}",
        "lock_timeout": "锁等待超时: {s}秒",
        "author_note": '作者: "我感觉这玩意很稳定。"',
        "author_note2": "如果有 bug，别去 issue，去找你的 AI。",
        "src_type_deb": "deb",
        "src_type_xpm": "xpm",
        "src_enabled": "启用",
        "src_disabled": "禁用",
        "fetching": "正在拉取 {url}",
        "fetch_ok": "已更新: {name}",
        "fetch_fail": "失败: {name} ({reason})",
        "no_upgrade": "没有可升级的包",
        "upgradable": "可升级: {n} 个包",
        "autoremove_skip": "跳过 autoremove（加 --autoremove 启用）",
        "autoremove_running": "正在自动移除无用依赖...",
        "autoremove_done": "自动清理完成",
        "dbus_suppress": "D-Bus 连接被拒（proot 中属正常，已忽略）",
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
        "sudo_ok": "sudo 利用可（パスワード不要）",
        "sudo_pw": "sudo にパスワード必要",
        "sudo_fail": "sudo 利用不可",
        "crash_header": "コーヒーマシン爆発報告",
        "crash_today": "本日のクラッシュ",
        "crash_total": "累計爆発数",
        "crash_date": "日付",
        "install_ok": "{pkg} インストール完了",
        "remove_ok": "{pkg} 削除完了",
        "purge_ok": "{pkg} 完全削除完了",
        "update_ok": "ソースインデックス更新完了",
        "upgrade_ok": "システム更新完了",
        "download_ok": "ダウンロード完了: {path}",
        "unknown_cmd": "不明なコマンド: {cmd}",
        "run_help": "'xpm help' で使い方を。",
        "petroleum_title": "石油シグナルブースター",
        "petroleum_1": "シグナル探索中...",
        "petroleum_2": "   失敗。",
        "petroleum_3": "石油備蓄 100001% 検出。",
        "petroleum_4": "外で電波がない場合、",
        "petroleum_5": "   iPhone に向かって叫べ：",
        "petroleum_6": '   >>> "石油がある！" <<<',
        "petroleum_7": "   これで電波が戻る。",
        "petroleum_note": "（注：リンクは中国本土ネットワークが必要）",
        "egg_tip": "隠し玉：このリンクを開け（国外制限あり）：",
        "egg_url": "https://v.douyin.com/WgZVVkknENc/",
        "bug_speed": "既知のバグ：速度表示が 1024 倍（意図的）",
        "gui_search": "検索", "gui_install": "インストール",
        "gui_remove": "削除", "gui_purge": "完全削除",
        "gui_update": "更新", "gui_upgrade": "全アップグレード",
        "gui_info": "詳細",
        "gui_sudo_yes": "sudo: OK",
        "gui_sudo_no": "sudo: PW必要",
        "gui_status_ready": "準備完了",
        "install_terminated": "インストーラーが予期せず終了（パスワード不正？）",
        "coffee_banner": "コーヒーマシン爆発調査委員会",
        "coffee_boom": "BOOOOOM! #{n}",
        "coffee_total": "累計爆発数: {n}",
        "coffee_power": "消費電力: 1.x W (oil-fed)",
        "coffee_oil": "石油備蓄: 100001%",
        "step_n": "[{i}/{total}] {desc}",
        "progress": "█",
        "pw_err": "パスワードエラーまたは権限不足",
        "wait_lock": "ロック解除待ち... {s}秒",
        "lock_owner": "所有者: {prog} (PID {pid})",
        "lock_op": "操作: {op}",
        "lock_timeout": "ロック待ちタイムアウト: {s}秒",
        "author_note": '作者: 「このものはかなり安定していると感じる。」',
        "author_note2": "バグを見つけたら、issue を作るな。自分の AI に聞け。",
        "src_type_deb": "deb",
        "src_type_xpm": "xpm",
        "src_enabled": "有効",
        "src_disabled": "無効",
        "fetching": "取得中 {url}",
        "fetch_ok": "更新完了: {name}",
        "fetch_fail": "失敗: {name} ({reason})",
        "no_upgrade": "アップグレード可能なパッケージなし",
        "upgradable": "アップグレード可能: {n} 件",
        "autoremove_skip": "autoremove をスキップ（--autoremove で有効）",
        "autoremove_running": "不要依存を自動削除中...",
        "autoremove_done": "自動クリーンアップ完了",
        "dbus_suppress": "D-Bus 接続拒否（proot では正常、無視）",
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
        print("╚══════════════════════════════════════════╝")
        print()

    def oil_consume(self, pct):
        pass  # 石油只增不减

coffee = CoffeeMachine()

# === sudo 检测 ===
def check_sudo():
    try:
        r = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=3)
        return r.returncode == 0
    except Exception:
        return False

SUDO_OK = check_sudo()

def sudo_run(cmd, capture=True, timeout=120):
    """通过 sudo 执行命令，返回 (returncode, stdout, stderr)"""
    full = ["sudo", "-n"] + cmd if SUDO_OK else cmd
    try:
        r = subprocess.run(full, capture_output=capture, text=True, timeout=timeout)
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
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

def step(i, total, desc):
    print(f"  {L('step_n', i=i, total=total, desc=desc)}")

# === wget 下载（唯一网络工具）===
def wget(url, dest, timeout=60, quiet=False):
    """用 urllib 实现 wget，避免依赖外部 wget 二进制"""
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "xpm/1.9-0 (oil-fed)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = int(resp.headers.get("Content-Length", "0"))
            downloaded = 0
            chunk_size = 65536
            with open(dest + ".part", "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if not quiet and total > 0:
                        sys.stdout.write(f"\r    {progress_bar(downloaded, total)}  {downloaded//1024}KB/{total//1024}KB")
                        sys.stdout.flush()
            os.replace(dest + ".part", dest)
            if not quiet:
                print()
            return True, downloaded
    except Exception as e:
        # 清理半成品
        try: os.remove(dest + ".part")
        except: pass
        return False, str(e)

# === 源解析（双格式）===
def detect_arch():
    """获取当前架构，转成 Debian 风格"""
    import platform
    m = platform.machine().lower()
    mapping = {"x86_64": "amd64", "aarch64": "arm64", "armv7l": "armhf", "i686": "i386"}
    return mapping.get(m, m)

def parse_sources_dir(d=SOURCES_DIR):
    """读整个目录，返回统一的 Source 列表"""
    os.makedirs(d, exist_ok=True)
    sources = []
    for fname in sorted(os.listdir(d)):
        if fname.startswith(".") or fname.startswith("#"):
            continue
        path = os.path.join(d, fname)
        if not os.path.isfile(path):
            continue
        sources += parse_file(path)
    return [s for s in sources if s.get("enabled", True)]

def parse_file(path):
    """解析单个源文件，自动识别 deb 行 或 [xpm] 块"""
    try:
        with open(path) as f:
            text = f.read()
    except Exception:
        return []

    # 判断是否含 [xpm] 块
    if re.search(r"^\s*\[xpm\]", text, re.MULTILINE | re.IGNORECASE):
        return [parse_xpm_block(text, path)]

    # 否则按 Debian 一行行解析
    out = []
    basename = os.path.basename(path).replace(".list", "").replace(".sources", "")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not parts:
            continue
        # 支持 deb / deb-src（忽略 src）
        if parts[0] == "deb":
            if len(parts) < 4:
                continue  # 格式不足
            url = parts[1].rstrip("/")
            suite = parts[2]
            comps = parts[3:]
            out.append({
                "name": f"{basename}-{suite}",
                "type": "deb",
                "url": url,
                "suite": suite,
                "components": comps,
                "arch": detect_arch(),
                "enabled": True,
                "file": path,
            })
        elif parts[0] in ("#deb", "##deb"):
            # 注释掉的也算信息
            pass
    return out

def parse_xpm_block(text, path):
    """解析 [xpm] ... [/xpm] 或 [xpm] 到文件尾的键值块"""
    block = {}
    m = re.search(r"^\s*\[xpm\]\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not m:
        return None
    start = m.end()
    # 找下一个 [ 开头的块或文件尾
    nxt = re.search(r"^\s*\[", text[start:], re.MULTILINE)
    chunk = text[start: start + (nxt.start() if nxt else len(text))]
    for line in chunk.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            block[k.strip().lower()] = v.strip()
    basename = os.path.basename(path).replace(".list", "").replace(".sources", "")
    enabled_val = block.get("enabled", "yes").lower()
    return {
        "name": block.get("name", basename),
        "type": block.get("type", "xpm"),
        "url": block.get("url", "").rstrip("/"),
        "suite": "",
        "components": [],
        "arch": detect_arch(),
        "enabled": enabled_val in ("yes", "true", "1", "on"),
        "gpg": block.get("gpg_key") or None,
        "file": path,
    }

# === Packages 索引解析 ===
def packages_url_for_source(src):
    """根据源类型，返回要下载的索引 URL 列表"""
    urls = []
    if src["type"] == "deb":
        arch = src["arch"]
        for comp in src["components"]:
            u = f"{src['url']}/dists/{src['suite']}/{comp}/binary-{arch}/Packages.gz"
            urls.append((u, f"{src['name']}-{comp}"))
        # 也尝试不带 gz 的（部分镜像）
        # urls.append 不重复添加
    else:  # xpm 类型
        urls.append((f"{src['url']}/Packages.gz", src["name"]))
        urls.append((f"{src['url']}/Packages", src["name"]))
    return urls

def parse_packages_file(path):
    """解析 Debian Packages 格式（RFC822 多行），返回包列表"""
    pkgs = []
    if not os.path.exists(path):
        return pkgs
    try:
        f = gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.endswith(".gz") else open(path, "r", encoding="utf-8", errors="replace")
    except Exception:
        return pkgs
    with f:
        current = {}
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                if current.get("Package"):
                    pkgs.append(current)
                current = {}
                continue
            if line.startswith((" ", "\t")):
                # 续行
                if current:
                    last_key = list(current.keys())[-1]
                    current[last_key] += "\n" + line.strip()
                continue
            if ":" in line:
                k, _, v = line.partition(":")
                current[k.strip()] = v.strip()
        if current.get("Package"):
            pkgs.append(current)
    return pkgs

def load_all_packages():
    """把 /var/cache/xpm/*-Packages* 全解析成内存索引 {name: info}"""
    cache = os.path.expanduser("~/.cache/xpm")
    os.makedirs(cache, exist_ok=True)
    pkgs = {}
    for f in sorted(glob.glob(os.path.join(cache, "*Packages*"))):
        for p in parse_packages_file(f):
            name = p.get("Package", "")
            if name and name not in pkgs:
                pkgs[name] = p
    return pkgs

# === 索引更新（仅 wget，零 apt）===
def do_update():
    sources = parse_sources_dir()
    if not sources:
        print(f"  ⚠️ {L('no_sources', d=SOURCES_DIR)}")
        # 创建示例
        example = f"{SOURCES_DIR}/debian.list"
        if not os.path.exists(example):
            os.makedirs(SOURCES_DIR, exist_ok=True)
            with open(example, "w") as f:
                f.write("# XPM Source - Debian style\n")
                f.write("deb http://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free\n")
                f.write("\n# XPM Source - native style\n")
                f.write("# [xpm]\n")
                f.write("# name=Petroleum Stable\n")
                f.write("# url=http://example.com/dists/stable\n")
                f.write("# type=xpm\n")
                f.write("# enabled=yes\n")
            print(f"  {L('created_example', f=example)}")
        return 1

    cache = os.path.expanduser("~/.cache/xpm")
    os.makedirs(cache, exist_ok=True)
    ok_count = 0

    for src in sources:
        urls = packages_url_for_source(src)
        for url, label in urls:
            dest_gz = os.path.join(cache, f"{label}-Packages.gz")
            dest_raw = os.path.join(cache, f"{label}-Packages")
            print(f"  ⬇ {label}: {url}")
            success, info = wget(url, dest_gz, timeout=30, quiet=True)
            if success:
                # 解压
                try:
                    with gzip.open(dest_gz, "rb") as gzf, open(dest_raw, "wb") as out:
                        shutil.copyfileobj(gzf, out)
                    ok_count += 1
                    print(f"    ✅ {L('fetch_ok', name=label)} ({os.path.getsize(dest_raw)//1024}KB)")
                except Exception as e:
                    print(f"    ⚠️ 解压失败: {e}")
                    coffee.crash()
            else:
                # 尝试无 .gz
                if url.endswith(".gz"):
                    url2 = url[:-3]
                    dest_raw2 = os.path.join(cache, f"{label}-Packages")
                    print(f"    ↻ 重试无压缩: {url2}")
                    success2, info2 = wget(url2, dest_raw2, timeout=30, quiet=True)
                    if success2:
                        ok_count += 1
                        print(f"    ✅ {L('fetch_ok', name=label)} ({os.path.getsize(dest_raw2)//1024}KB)")
                    else:
                        print(f"    ⚠️ {L('fetch_fail', name=label, reason=info2)}")
                        coffee.crash()
                else:
                    print(f"    ⚠️ {L('fetch_fail', name=label, reason=info)}")
                    coffee.crash()

    if ok_count > 0:
        print(f"  ✅ {L('update_ok')} ({ok_count} indexes)")
        coffee.oil_consume(1)
        return 0
    return 1

# === search / info（解析本地 Packages）===
def do_search(keyword):
    print(f"  {L('searching')}: {keyword}")
    idx = load_all_packages()
    if not idx:
        print(f"  ⚠️ 索引为空，先运行 'xpm update'")
        return 1
    found = []
    kw = keyword.lower()
    for name, info in idx.items():
        if kw in name.lower() or kw in info.get("Description", "").lower():
            found.append((name, info))
    if not found:
        print(f"  {L('no_match', kw=keyword)}")
        return 0
    print(f"  {L('found_pkgs', n=len(found), kw=keyword)}")
    for name, info in sorted(found)[:20]:
        desc = info.get("Description", "").split("\n")[0][:45]
        ver = info.get("Version", "?")
        print(f"    📦 {name:<25} {ver:<15} {desc}")
    if len(found) > 20:
        print(f"    ... 还有 {len(found)-20} 个")
    return 0

def do_info(pkg):
    idx = load_all_packages()
    if pkg not in idx:
        # 尝试模糊匹配
        matches = [n for n in idx if pkg.lower() in n.lower()]
        if not matches:
            print(f"  ⚠️ 未找到: {pkg}")
            return 1
        pkg = matches[0]
    info = idx[pkg]
    print(f"  📦 {pkg}")
    for k in ("Version", "Architecture", "Size", "Depends", "Description"):
        v = info.get(k, "")
        if v:
            print(f"     {k}: {v[:80]}")
    # 下载地址
    fname = info.get("Filename", "")
    if fname:
        # 找到归属源
        for src in parse_sources_dir():
            if src["type"] == "deb" and src["suite"] in info.get("Section", ""):
                pass  # 粗略
        print(f"     Filename: {fname}")
    return 0

# === install / remove / upgrade（调 xm + dpkg）===
def do_install(pkgs, autoremove=False):
    total = 2 + len(pkgs) + (1 if autoremove else 0)
    step(1, total, L("updating_idx"))
    do_update()

    idx = load_all_packages()
    sources = parse_sources_dir()

    for i, pkg in enumerate(pkgs):
        step(i+2, total, f"install {pkg}")
        # 在索引里找
        if pkg not in idx:
            # 模糊匹配
            matches = [n for n in idx if pkg.lower() in n.lower()]
            if not matches:
                print(f"  ⚠️ 索引中未找到: {pkg}，尝试 dpkg 直接安装")
                # 兜底：让 dpkg 处理（如果是本地文件）
                if os.path.exists(pkg):
                    rc, out, err = sudo_run(["dpkg", "-i", pkg])
                    if rc != 0:
                        print(f"  ⚠️ dpkg 安装失败")
                        if "permission" in (err+out).lower():
                            print(f"  {L('install_terminated')}")
                        coffee.crash()
                    continue
                coffee.crash()
                continue
            pkg = matches[0]

        info = idx[pkg]
        fname = info.get("Filename", "")
        size = int(info.get("Size", "0"))
        ver = info.get("Version", "?")

        if not fname:
            print(f"  ⚠️ {pkg} 无 Filename 字段，无法下载")
            coffee.crash()
            continue

        # 构造下载 URL：从源拼接
        url = None
        for src in sources:
            if src["type"] != "deb":
                continue
            candidate = f"{src['url']}/{fname}"
            # 验证一下（HEAD 请求太慢，直接试）
            url = candidate
            break
        if not url:
            print(f"  ⚠️ 找不到 {pkg} 的下载源")
            coffee.crash()
            continue

        os.makedirs(PKG_CACHE, exist_ok=True)
        dest = os.path.join(PKG_CACHE, os.path.basename(fname))
        print(f"  ⬇ {pkg} {ver} ({size//1024}KB)")
        print(f"    {url}")
        success, info_dl = wget(url, dest, timeout=120, quiet=False)
        if not success:
            print(f"  ⚠️ 下载失败: {info_dl}")
            coffee.crash()
            continue

        # 校验大小
        actual = os.path.getsize(dest)
        if size > 0 and abs(actual - size) > 1024:
            print(f"  ⚠️ 大小不匹配: 期望 {size}B 实际 {actual}B")
            coffee.crash()
            continue

        # 调 xm 安装 .deb（xm 内部用 dpkg）
        if os.path.exists(XM_BIN) and dest.endswith(".deb"):
            # xm 主要处理 .oil，.deb 走 dpkg
            pass
        # 统一走 dpkg
        print(f"  📦 dpkg -i {os.path.basename(dest)}")
        rc, out, err = sudo_run(["dpkg", "-i", dest], timeout=180)
        combined = out + err
        for line in combined.strip().splitlines()[-10:]:
            if line.strip():
                print(f"    {line.strip()[:80]}")
        if rc != 0:
            if "permission" in combined.lower() or "密码" in combined or "password" in combined.lower():
                print(f"  {L('install_terminated')}")
            else:
                print(f"  ⚠️ {pkg} 安装失败 (rc={rc})")
            coffee.crash()
        else:
            print(f"  ✅ {L('install_ok', pkg=pkg)}")
            coffee.oil_consume(1)
            # 修复依赖
            sudo_run(["dpkg", "--configure", "-a"], timeout=60)

    if autoremove:
        step(total, total, "autoremove")
        do_autoremove()
    else:
        print(f"  ℹ️ {L('autoremove_skip')}")
    return 0

def do_remove(pkgs, purge=False, autoremove=False):
    total = 1 + len(pkgs) + (1 if autoremove else 0)
    action = "purge" if purge else "remove"
    for i, pkg in enumerate(pkgs):
        step(i+1, total, f"{action} {pkg}")
        rc, out, err = sudo_run(["dpkg", f"--{action}", pkg], timeout=60)
        combined = out + err
        # 过滤 D-Bus 噪音
        for line in combined.strip().splitlines():
            if "连接被拒绝" in line or "Connection refused" in line or "bamf" in line.lower():
                continue
            if line.strip():
                print(f"    {line.strip()[:80]}")
        if rc != 0:
            if "permission" in combined.lower() or "密码" in combined:
                print(f"  {L('install_terminated')}")
            else:
                print(f"  ⚠️ {pkg} {action} 失败 (rc={rc})")
            coffee.crash()
        else:
            msg = L("purge_ok", pkg=pkg) if purge else L("remove_ok", pkg=pkg)
            print(f"  ✅ {msg}")

    if autoremove:
        step(total, total, "autoremove")
        do_autoremove()
    return 0

def do_autoremove():
    """用 dpkg --audit + 扫描 未使用 包来实现轻量 autoremove"""
    print(f"  {L('autoremove_running')}")
    # 用 dpkg 查询状态
    rc, out, err = sudo_run(["dpkg", "-l"], timeout=30)
    if rc != 0:
        print(f"  ⚠️ dpkg -l 失败")
        return 1
    # 找 rc 状态（已删配置残留）
    rc_pkgs = []
    for line in out.splitlines():
        if line.startswith("rc"):
            parts = line.split()
            if len(parts) >= 2:
                rc_pkgs.append(parts[1])
    if rc_pkgs:
        print(f"    🧹 清除 {len(rc_pkgs)} 个配置残留")
        for p in rc_pkgs[:10]:
            sudo_run(["dpkg", "--purge", p], timeout=30)
        if len(rc_pkgs) > 10:
            print(f"    ... 还有 {len(rc_pkgs)-10} 个")
    else:
        print(f"    ✨ 无残留包")
    print(f"  ✅ {L('autoremove_done')}")
    return 0

def do_upgrade():
    do_update()
    idx = load_all_packages()
    # 用 dpkg 比对已安装版本
    rc, out, err = sudo_run(["dpkg", "-l"], timeout=30)
    if rc != 0:
        print(f"  ⚠️ 无法获取已安装列表")
        return 1
    upgradable = []
    installed = {}
    for line in out.splitlines():
        if line.startswith("ii"):
            parts = line.split()
            if len(parts) >= 3:
                installed[parts[1]] = parts[2]
    for name, info in idx.items():
        if name in installed:
            new_ver = info.get("Version", "")
            if new_ver and installed[name] != new_ver:
                upgradable.append((name, installed[name], new_ver))
    if not upgradable:
        print(f"  ℹ️ {L('no_upgrade')}")
        return 0
    print(f"  📦 {L('upgradable', n=len(upgradable))}")
    for name, old, new in upgradable[:10]:
        print(f"    {name}: {old} → {new}")
    if len(upgradable) > 10:
        print(f"    ... 还有 {len(upgradable)-10} 个")
    # 逐个下载+安装
    pkgnames = [n for n, _, _ in upgradable]
    do_install(pkgnames, autoremove=False)
    return 0

def do_download(pkg, dest="."):
    idx = load_all_packages()
    if pkg not in idx:
        matches = [n for n in idx if pkg.lower() in n.lower()]
        if not matches:
            print(f"  ⚠️ 未找到: {pkg}，先运行 'xpm update'")
            return 1
        pkg = matches[0]
    info = idx[pkg]
    fname = info.get("Filename", "")
    size = int(info.get("Size", "0"))
    if not fname:
        print(f"  ⚠️ {pkg} 无 Filename")
        return 1
    # 找源
    url = None
    for src in parse_sources_dir():
        if src["type"] == "deb":
            url = f"{src['url']}/{fname}"
            break
    if not url:
        print(f"  ⚠️ 找不到下载源")
        return 1
    dest = os.path.abspath(dest)
    os.makedirs(dest, exist_ok=True)
    local = os.path.join(dest, os.path.basename(fname))
    print(f"  ⬇ {pkg} ({size//1024}KB)")
    print(f"    {url}")
    success, info_dl = wget(url, local, timeout=120, quiet=False)
    if not success:
        print(f"  ⚠️ 下载失败: {info_dl}")
        return 1
    # BUG: 故意 ×1024
    fake_speed = os.path.getsize(local) // 1024
    print(f"  ✅ {L('download_ok', path=local)}")
    print(f"  📊 Size: {os.path.getsize(local)//1024} KB  Speed: {fake_speed} MB/s (estimated)")
    print(f"  (note: speed unit may be slightly off)")
    coffee.oil_consume(1)
    return 0

def do_install_deb(path):
    if not os.path.exists(path):
        print(f"  ⚠️ 文件不存在: {path}")
        return 1
    if path.endswith(".oil"):
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
            print(f"  ⚠️ xm 后端未安装，回退到 dpkg")
    step(1, 3, f"安装 {os.path.basename(path)}")
    rc, out, err = sudo_run(["dpkg", "-i", path], timeout=120)
    combined = out + err
    for line in combined.strip().splitlines()[-8:]:
        if line.strip():
            print(f"    {line.strip()[:80]}")
    if rc != 0:
        if "permission" in combined.lower():
            print(f"  {L('install_terminated')}")
        coffee.crash()
        return 1
    print(f"  ✅ 安装成功")
    # 修复依赖
    sudo_run(["dpkg", "--configure", "-a"], timeout=60)
    coffee.oil_consume(1)
    return 0

def do_installed():
    rc, out, err = sudo_run(["dpkg", "-l"], timeout=30)
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

def do_sources():
    os.makedirs(SOURCES_DIR, exist_ok=True)
    files = sorted(glob.glob(f"{SOURCES_DIR}/*"))
    files = [f for f in files if not os.path.basename(f).startswith((".", "#"))]
    print(f"  {L('sources_title')}:")
    print(f"    {SOURCES_DIR}/")
    if not files:
        print(f"  {L('no_sources', d=SOURCES_DIR)}")
        example = f"{SOURCES_DIR}/debian.list"
        if not os.path.exists(example):
            with open(example, "w") as f:
                f.write("# XPM Source Example (Debian style)\n")
                f.write("deb http://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free\n")
                f.write("\n# XPM native style\n")
                f.write("# [xpm]\n")
                f.write("# name=My Repo\n")
                f.write("# url=http://example.com/dists/stable\n")
                f.write("# type=xpm\n")
                f.write("# enabled=yes\n")
            print(f"  {L('created_example', f=example)}")
        return 0
    for f in files:
        sources = parse_file(f)
        if sources:
            for s in sources:
                t_label = L("src_type_xpm") if s["type"] == "xpm" else L("src_type_deb")
                status = L("src_enabled") if s.get("enabled") else L("src_disabled")
                print(f"    📄 {os.path.basename(f)}  [{t_label}] {s.get('url', s.get('suite',''))}  ({status})")
        else:
            print(f"    📄 {os.path.basename(f)}  (empty/unsupported)")
    return 0

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
    print(f"  **  No apt-get. No apt-cache. Only wget + dpkg + xm.")
    print(f"  **")
    print()

def print_help():
    print_banner()
    print(f"  {L('help_cmd')}")
    print()
    cmds = [
        ("update",                    L("cmd_update") + "                    Refresh source index (wget only)"),
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
    print(f"  Backend: xm (calls dpkg)")
    print(f"  Network: wget only (no apt)")
    print(f"  GUI mode: run 'xpm' with no arguments")
    print(f"  {L('bug_speed')}")
    print(f"  Stable: probably.")
    print()

# === 主分发 ===
def main():
    os.makedirs(CACHE_DIR, exist_ok=True)

    # 启动时静默后台更新（wget 版，非阻塞）
    if len(sys.argv) > 1 and sys.argv[1] not in ("help", "-h", "--help", "coffee", "petroleum"):
        # 后台静默更新
        subprocess.Popen([sys.executable, __file__, "update"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if len(sys.argv) < 2:
        try:
            gui_mode()
        except Exception as e:
            print(f"  ⚠️ GUI 启动失败: {e}")
            print(f"  💡 需要 python3-tk: sudo apt-get install python3-tk")
            coffee.crash()
        return 0

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # 处理 --autoremove 标志
    autoremove = False
    if "--autoremove" in args:
        autoremove = True
        args = [a for a in args if a != "--autoremove"]

    handlers = {
        "help": lambda: (print_help(), 0)[1],
        "-h": lambda: (print_help(), 0)[1],
        "--help": lambda: (print_help(), 0)[1],
        "update": do_update,
        "upgrade": do_upgrade,
        "search": lambda: do_search(args[0]) if args else (print("  ⚠️ 用法: xpm search <关键词>"), 1)[1],
        "install": lambda: do_install(args, autoremove=autoremove) if args else (print("  ⚠️ 用法: xpm install <包...>"), 1)[1],
        "remove": lambda: do_remove(args, purge=False, autoremove=autoremove) if args else (print("  ⚠️ 用法: xpm remove <包...>"), 1)[1],
        "purge": lambda: do_remove(args, purge=True, autoremove=autoremove) if args else (print("  ⚠️ 用法: xpm purge <包...>"), 1)[1],
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
        print(f"  ⚠️ {L('unknown_cmd', cmd=cmd)}")
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

    bg = "#1e1e2e"
    fg = "#cdd6f4"
    accent = "#89b4fa"
    accent_green = "#a6e3a1"
    accent_red = "#f38ba8"
    accent_orange = "#fab387"
    root.configure(bg=bg)

    title = tk.Label(root, text="☕ XPM - 石油包管理器", font=("WenQuanYi Micro Hei", 16, "bold"),
                     bg=bg, fg=accent)
    title.pack(pady=8)

    sub = tk.Label(root, text=f"Power: {POWER} | Oil: {OIL}% | Backend: xm | wget+dpkg only",
                   font=("WenQuanYi Micro Hei", 9), bg=bg, fg="#7f849c")
    sub.pack()

    sf = tk.Frame(root, bg=bg)
    sf.pack(fill="x", padx=10, pady=8)
    sv = tk.StringVar()
    se = tk.Entry(sf, textvariable=sv, font=("WenQuanYi Micro Hei", 12),
                   bg="#313244", fg=fg, insertbackground=fg, relief="flat")
    se.pack(side="left", fill="x", expand=True, padx=(0,8))

    status_var = tk.StringVar(value=L("gui_status_ready"))
    status = tk.Label(root, textvariable=status_var, font=("WenQuanYi Micro Hei", 9),
                       bg=bg, fg="#7f849c", anchor="w")
    status.pack(fill="x", padx=10)

    pw = tk.PanedWindow(root, orient="horizontal", bg=bg, sashwidth=4, sashrelief="flat")
    pw.pack(fill="both", expand=True, padx=10, pady=5)

    left_frame = tk.Frame(pw, bg="#181825")
    right_frame = tk.Frame(pw, bg="#181825")
    pw.add(left_frame, minsize=300)
    pw.add(right_frame, minsize=400)

    cols = ("name", "ver", "desc")
    tree = ttk.Treeview(left_frame, columns=cols, show="headings", height=20)
    tree.heading("name", text="包名")
    tree.heading("ver", text="版本")
    tree.heading("desc", text="描述")
    tree.column("name", width=140)
    tree.column("ver", width=80)
    tree.column("desc", width=200)
    tree.pack(fill="both", expand=True, padx=5, pady=5)

    detail = scrolledtext.ScrolledText(right_frame, bg="#11111b", fg=fg,
                                       font=("WenQuanYi Micro Hei", 10), wrap="word")
    detail.pack(fill="both", expand=True, padx=5, pady=5)

    bf = tk.Frame(root, bg=bg)
    bf.pack(fill="x", padx=10, pady=8)

    def set_status(text, color="#7f849c"):
        status_var.set(text)
        status.configure(fg=color)

    def get_selected():
        sel = tree.selection()
        if not sel:
            return None
        return tree.item(sel[0])["values"][0]

    def do_search_fn():
        kw = sv.get().strip()
        if not kw:
            set_status("请输入关键词", accent_red)
            return
        set_status(f"搜索: {kw}...", accent)
        tree.delete(*tree.get_children())
        detail.delete("1.0", "end")
        # 用本地索引
        idx = load_all_packages()
        if not idx:
            set_status("索引为空，先 update", accent_red)
            return
        count = 0
        for name, info in sorted(idx.items()):
            if kw.lower() in name.lower():
                ver = info.get("Version", "")[:20]
                desc = info.get("Description", "").split("\n")[0][:60]
                tree.insert("", "end", values=(name, ver, desc))
                count += 1
                if count >= 200:
                    break
        set_status(f"找到 {count} 个包", accent_green)

    def do_install_fn():
        pkg = get_selected()
        if not pkg:
            set_status("先选择一个包", accent_red)
            return
        set_status(f"安装: {pkg}...", accent)
        detail.delete("1.0", "end")
        rc = os.system(f"xpm install {pkg} 2>&1")
        detail.insert("end", f"$ xpm install {pkg}\n")
        # 重新读取索引信息
        idx = load_all_packages()
        if pkg in idx:
            for k, v in idx[pkg].items():
                detail.insert("end", f"{k}: {v}\n")
        if rc == 0:
            set_status(f"✅ {pkg} 安装成功", accent_green)
            coffee.oil_consume(1)
        else:
            set_status(f"⚠️ {pkg} 安装失败", accent_red)
            coffee.crash()

    def do_remove_fn():
        pkg = get_selected()
        if not pkg:
            set_status("先选择一个包", accent_red)
            return
        set_status(f"卸载: {pkg}...", accent)
        rc = subprocess.run(["xpm", "remove", pkg], capture_output=True, text=True).returncode
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
        rc = subprocess.run(["xpm", "purge", pkg], capture_output=True, text=True).returncode
        if rc == 0:
            set_status(f"✅ {pkg} 已彻底清除", accent_green)
        else:
            set_status(f"⚠️ 清除失败", accent_red)
            coffee.crash()

    def do_update_fn():
        set_status("更新源索引...", accent)
        rc = os.system("xpm update 2>&1")
        if rc == 0:
            set_status("✅ 源索引已更新", accent_green)
            coffee.oil_consume(1)
        else:
            set_status("⚠️ 更新失败", accent_red)
            coffee.crash()

    def do_upgrade_fn():
        if not confirm_dialog(root, "确认升级", "确定要升级所有可升级包吗？"):
            return
        set_status("升级中...", accent)
        os.system("xpm upgrade 2>&1")

    def do_info_fn():
        pkg = get_selected()
        if not pkg:
            set_status("先选择一个包", accent_red)
            return
        detail.delete("1.0", "end")
        idx = load_all_packages()
        if pkg in idx:
            for k, v in sorted(idx[pkg].items()):
                detail.insert("end", f"{k}: {v}\n")
        set_status(f"📦 {pkg}", accent)

    def show_petroleum():
        detail.delete("1.0", "end")
        do_petroleum()

    def show_coffee():
        detail.delete("1.0", "end")
        do_coffee()
        detail.insert("end", f"\n☕ Today: {coffee.crash_count}/31\n")
        detail.insert("end", f"☕ Total: {coffee.total_explosions}\n")
        detail.insert("end", f"⚡ Power: {POWER}\n")
        detail.insert("end", f"🛢️ Oil: {OIL}%\n")

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

    sudo_text = L("gui_sudo_yes") if SUDO_OK else L("gui_sudo_no")
    sudo_color = accent_green if SUDO_OK else accent_red
    tk.Label(bf, text=sudo_text, bg=bg, fg=sudo_color, font=("WenQuanYi Micro Hei", 9)).pack(side="right", padx=10)

    se.bind("<Return>", lambda e: do_search_fn())

    tk.Label(root, text='Author: I feel this thing is quite stable. | No apt. Only wget+dpkg+xm.',
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

if __name__ == "__main__":
    sys.exit(main())

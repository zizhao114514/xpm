"""
X-Store GUI 核心逻辑
不依赖 tkinter，纯数据 + 状态管理
GUI 前端（tk/app）调用这里的接口
"""

import os, threading, time
from typing import List, Dict, Optional, Callable

# 兼容直接运行和包内导入
try:
    from ...store import (
        get_categories, get_apps_by_category, get_top_apps,
        search_apps, get_app_detail, rate_app, get_rating,
        add_custom, remove_custom, get_all_apps,
    )
    from ...store.catalog import load_ratings, save_ratings
    from ...core.installer import get_engine
    from ...core.statusdb import get_db
except (ValueError, ImportError):
    from xpm_suite.store import (
        get_categories, get_apps_by_category, get_top_apps,
        search_apps, get_app_detail, rate_app, get_rating,
        add_custom, remove_custom, get_all_apps,
    )
    from xpm_suite.store.catalog import load_ratings, save_ratings
    from xpm_suite.core.installer import get_engine
    from xpm_suite.core.statusdb import get_db

try:
    from .theme import get_theme, THEMES, DEFAULT_THEME
except (ImportError, ValueError):
    from xpm_suite.store.gui.theme import get_theme, THEMES, DEFAULT_THEME

# === 全局状态 ===

class StoreState:
    """GUI 全局状态（被 tkinter 和 CLI 共享）"""

    def __init__(self):
        self.theme_name = DEFAULT_THEME
        self.theme = get_theme(self.theme_name)
        self.current_category = "system"
        self.search_query = ""
        self.selected_app = None
        self.installed_filter = False
        self._db = get_db()
        self._engine = get_engine()
        self._callbacks = []
        self._download_progress = {}  # app_name -> {pct, speed, eta}

    def set_theme(self, name: str):
        if name in THEMES:
            self.theme_name = name
            self.theme = get_theme(name)
            self._notify()

    def cycle_theme(self):
        names = list(THEMES.keys())
        idx = names.index(self.theme_name)
        self.set_theme(names[(idx + 1) % len(names)])

    def set_category(self, cat: str):
        self.current_category = cat
        self.search_query = ""
        self._notify()

    def set_search(self, query: str):
        self.search_query = query
        self._notify()

    def select_app(self, name: str):
        self.selected_app = name
        self._notify()

    def toggle_installed_filter(self):
        self.installed_filter = not self.installed_filter
        self._notify()

    def get_visible_apps(self) -> List[dict]:
        """获取当前可见的应用列表"""
        if self.search_query:
            apps = search_apps(self.search_query, limit=50)
        elif self.current_category == "__top__":
            apps = get_top_apps(30)
        elif self.current_category == "__installed__":
            installed_names = {p.name for p in self._db.installed_packages()}
            all_apps = get_all_apps()
            apps = []
            for name in installed_names:
                if name in all_apps:
                    apps.append(all_apps[name])
        else:
            apps = get_apps_by_category(self.current_category)

        if self.installed_filter and self.current_category not in ("__installed__",):
            installed_names = {p.name for p in self._db.installed_packages()}
            apps = [a for a in apps if a.get("name") in installed_names]

        return apps

    def get_app_detail(self, name: str) -> Optional[dict]:
        return get_app_detail(name)

    def is_installed(self, name: str) -> bool:
        """检查应用是否已安装（含其依赖包）"""
        detail = get_app_detail(name)
        if not detail:
            return self._db.is_installed(name)
        deps = detail.get("deps", detail.get("packages", []))
        if not deps:
            return self._db.is_installed(name)
        return all(self._db.is_installed(d) for d in deps)

    def install_app(self, name: str, progress_cb: Optional[Callable] = None) -> bool:
        """安装应用"""
        detail = get_app_detail(name)
        if not detail:
            return False

        deps = detail.get("deps", detail.get("packages", []))
        if not deps:
            deps = [name]

        def _do_install():
            for pkg in deps:
                try:
                    self._engine.install(pkg, progress_cb)
                except Exception as e:
                    if progress_cb:
                        progress_cb(-1, 0, f"❌ {pkg}: {e}")
                    return False
            if progress_cb:
                progress_cb(100, 100, "✅ 完成")
            self._notify()
            return True

        if progress_cb:
            threading.Thread(target=_do_install, daemon=True).start()
            return True
        return _do_install()

    def remove_app(self, name: str) -> bool:
        detail = get_app_detail(name)
        if not detail:
            return False
        deps = detail.get("deps", detail.get("packages", []))
        if not deps:
            deps = [name]
        for dep_name in deps:
            try:
                self._engine.remove(dep_name)
            except Exception:
                pass
        self._notify()
        return True

    def rate_app(self, name: str, stars: int, comment: str = "") -> float:
        avg = rate_app(name, stars, comment)
        self._notify()
        return avg

    def get_rating(self, name: str) -> dict:
        return get_rating(name)

    def get_categories(self) -> List[dict]:
        return get_categories()

    def get_theme_names(self) -> List[str]:
        return list(THEMES.keys())

    def subscribe(self, callback: Callable):
        self._callbacks.append(callback)

    def _notify(self):
        for cb in self._callbacks:
            try:
                cb()
            except Exception:
                pass

# === 单例 ===

_state: Optional[StoreState] = None

def get_state() -> StoreState:
    global _state
    if _state is None:
        _state = StoreState()
    return _state

# === 格式化工具 ===

def format_stars(avg: float, count: int = 0) -> str:
    """返回星星字符串"""
    if count == 0:
        return "☆☆☆☆☆ 未评分"
    full = int(avg)
    half = 1 if avg - full >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + "⯨" * half + "☆" * empty + f" {avg:.1f} ({count})"

def format_popularity_bar(pop: int, width: int = 10) -> str:
    filled = int(width * pop / 100)
    return "█" * filled + "░" * (width - filled)

def get_app_icon(name: str) -> str:
    """根据应用名返回 emoji 图标"""
    icons = {
        "htop": "📊", "btop": "📈", "neofetch": "🖥️", "ncdu": "💽",
        "tmux": "🖥️", "tree": "🌳", "fzf": "🔍",
        "vim": "✏️", "emacs": "🐰", "git": "🔀", "python3": "🐍",
        "nodejs": "🟢", "build-essential": "🔧",
        "curl": "🌐", "wget": "⬇️", "nmap": "🗺️",
        "openssh-client": "🔑", "rsync": "🔄",
        "ffmpeg": "🎬", "imagemagick": "🖼️", "mpv": "🎞️",
        "gnupg": "🔐", "fail2ban": "🛡️",
        "cowsay": "🐄", "figlet": "🔤", "sl": "🚂",
        "fortune": "🎯", "lolcat": "🌈",
    }
    return icons.get(name, "📦")

def get_format_badge(source_format: str) -> str:
    return "📦 .deb" if source_format == "deb" else "🛢️ .oil"

# === 进度模拟 ===

class ProgressTracker:
    """跟踪多个下载进度"""

    def __init__(self):
        self._progress: Dict[str, dict] = {}
        self._listeners = []

    def update(self, app_name: str, pct: int, speed: str = "", eta: str = ""):
        self._progress[app_name] = {
            "pct": max(0, min(100, pct)),
            "speed": speed, "eta": eta,
            "time": time.time(),
        }
        self._notify()

    def get(self, app_name: str) -> dict:
        return self._progress.get(app_name, {"pct": 0, "speed": "", "eta": ""})

    def all(self) -> Dict[str, dict]:
        return dict(self._progress)

    def clear(self, app_name: str = ""):
        if app_name:
            self._progress.pop(app_name, None)
        else:
            self._progress.clear()
        self._notify()

    def subscribe(self, cb: Callable):
        self._listeners.append(cb)

    def _notify(self):
        for cb in self._listeners:
            try: cb()
            except: pass

# === 桌面集成 ===

def create_desktop_file(install_dir: str = "/usr/share/applications") -> str:
    """创建 X-Store GUI 的 .desktop 文件"""
    content = """[Desktop Entry]
Version=1.0
Type=Application
Name=X-Store
GenericName=App Store
Comment=XPM Suite 应用商店
Exec=xstore-gui
Icon=package-x-generic
Terminal=false
Categories=System;PackageManager;
Keywords=package;install;remove;update;app store;
StartupNotify=true
"""
    path = os.path.join(install_dir, "xstore-gui.desktop")
    try:
        os.makedirs(install_dir, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        os.chmod(path, 0o644)
        return path
    except PermissionError:
        # 用户目录
        user_dir = os.path.expanduser("~/.local/share/applications")
        os.makedirs(user_dir, exist_ok=True)
        path = os.path.join(user_dir, "xstore-gui.desktop")
        with open(path, "w") as f:
            f.write(content)
        os.chmod(path, 0o644)
        return path

# === 测试入口 ===

if __name__ == "__main__":
    state = get_state()
    print(f"=== X-Store GUI 核心 ===")
    print(f"主题: {state.theme_name} ({state.theme['name']})")
    print(f"分类: {[c['key'] for c in state.get_categories()]}")
    print(f"\n热门 TOP 5:")
    for a in state.get_visible_apps()[:5]:
        print(f"  {get_app_icon(a['name'])} {a['display']:<20} "
              f"{format_popularity_bar(a.get('popularity',0))}")
    print(f"\nhtop 详情:")
    d = state.get_app_detail("htop")
    if d:
        print(f"  描述: {d['desc']}")
        print(f"  评分: {format_stars(d.get('rating_avg',0), d.get('rating_count',0))}")
        print(f"  主页: {d.get('homepage','')}")

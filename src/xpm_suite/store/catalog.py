"""
X-Store 应用目录
内置应用分类数据库，美观展示
"""

import json, os, time
from typing import List, Dict, Optional
from pathlib import Path

STORE_DIR = Path("/var/lib/xstore")
CATALOG_FILE = STORE_DIR / "catalog.json"
RATINGS_FILE = STORE_DIR / "ratings.json"
CUSTOM_FILE = STORE_DIR / "custom.json"

# === 内置应用目录 ===

BUILTIN_APPS = {
    "system": {
        "icon": "⚙️",
        "label": "系统工具",
        "apps": {
            "htop": {
                "name": "htop", "display": "htop",
                "desc": "交互式进程查看器，彩色界面，支持鼠标",
                "category": "system", "tags": ["监控", "进程", "终端"],
                "popularity": 95, "homepage": "https://htop.dev",
                "deps": ["libncursesw6", "libtinfo6"],
            },
            "btop": {
                "name": "btop", "display": "btop",
                "desc": "资源监控神器，CPU/内存/磁盘/网络全彩显示",
                "category": "system", "tags": ["监控", "炫酷", "资源"],
                "popularity": 90, "homepage": "https://github.com/aristocratos/btop",
                "deps": [],
            },
            "neofetch": {
                "name": "neofetch", "display": "neofetch",
                "desc": "系统信息展示工具，截图装逼必备",
                "category": "system", "tags": ["系统信息", "炫酷"],
                "popularity": 88, "homepage": "https://github.com/dylanaraps/neofetch",
                "deps": ["bash"],
            },
            "ncdu": {
                "name": "ncdu", "display": "ncdu",
                "desc": "磁盘使用分析器，快速找出大文件",
                "category": "system", "tags": ["磁盘", "分析"],
                "popularity": 82, "homepage": "",
                "deps": [],
            },
            "tmux": {
                "name": "tmux", "display": "tmux",
                "desc": "终端复用器，会话保持，分屏利器",
                "category": "system", "tags": ["终端", "多路复用"],
                "popularity": 85, "homepage": "https://github.com/tmux/tmux",
                "deps": ["libevent-2.1-7"],
            },
            "tree": {
                "name": "tree", "display": "tree",
                "desc": "以树状图列出目录内容",
                "category": "system", "tags": ["目录", "查看"],
                "popularity": 70, "homepage": "",
                "deps": [],
            },
            "fzf": {
                "name": "fzf", "display": "fzf",
                "desc": "模糊搜索神器，终端里的 Ctrl+P",
                "category": "system", "tags": ["搜索", "效率"],
                "popularity": 80, "homepage": "https://github.com/junegunn/fzf",
                "deps": [],
            },
        },
    },
    "dev": {
        "icon": "💻",
        "label": "开发工具",
        "apps": {
            "vim": {
                "name": "vim", "display": "Vim",
                "desc": "经典文本编辑器，号称编辑器之神",
                "category": "dev", "tags": ["编辑器", "终端"],
                "popularity": 92, "homepage": "https://www.vim.org",
                "deps": [],
            },
            "emacs": {
                "name": "emacs", "display": "Emacs",
                "desc": "可扩展的文本编辑器，伪装成操作系统的编辑器",
                "category": "dev", "tags": ["编辑器", "Lisp"],
                "popularity": 75, "homepage": "https://www.gnu.org/software/emacs/",
                "deps": [],
            },
            "git": {
                "name": "git", "display": "Git",
                "desc": "分布式版本控制系统",
                "category": "dev", "tags": ["版本控制", "必备"],
                "popularity": 98, "homepage": "https://git-scm.com",
                "deps": [],
            },
            "python3": {
                "name": "python3", "display": "Python 3",
                "desc": "Python 3 解释器",
                "category": "dev", "tags": ["语言", "脚本"],
                "popularity": 95, "homepage": "https://www.python.org",
                "deps": [],
            },
            "nodejs": {
                "name": "nodejs", "display": "Node.js",
                "desc": "JavaScript 运行时，前端后端通吃",
                "category": "dev", "tags": ["JS", "运行时"],
                "popularity": 88, "homepage": "https://nodejs.org",
                "deps": [],
            },
            "build-essential": {
                "name": "build-essential", "display": "开发基础套件",
                "desc": "C/C++ 编译工具链（gcc, g++, make, libc-dev）",
                "category": "dev", "tags": ["C/C++", "编译"],
                "popularity": 90, "homepage": "",
                "deps": [],
            },
        },
    },
    "network": {
        "icon": "🌐",
        "label": "网络工具",
        "apps": {
            "curl": {
                "name": "curl", "display": "cURL",
                "desc": "命令行 URL 数据传输工具，支持多种协议",
                "category": "network", "tags": ["下载", "HTTP", "API"],
                "popularity": 93, "homepage": "https://curl.se",
                "deps": [],
            },
            "wget": {
                "name": "wget", "display": "Wget",
                "desc": "GNU 文件下载工具，支持递归下载",
                "category": "network", "tags": ["下载"],
                "popularity": 85, "homepage": "https://www.gnu.org/software/wget/",
                "deps": [],
            },
            "nmap": {
                "name": "nmap", "display": "Nmap",
                "desc": "网络探测和安全审计工具",
                "category": "network", "tags": ["扫描", "安全"],
                "popularity": 80, "homepage": "https://nmap.org",
                "deps": [],
            },
            "openssh-client": {
                "name": "openssh-client", "display": "OpenSSH Client",
                "desc": "SSH 远程登录客户端",
                "category": "network", "tags": ["SSH", "远程"],
                "popularity": 90, "homepage": "https://www.openssh.com",
                "deps": [],
            },
            "rsync": {
                "name": "rsync", "display": "Rsync",
                "desc": "快速增量文件传输工具",
                "category": "network", "tags": ["同步", "备份"],
                "popularity": 78, "homepage": "",
                "deps": [],
            },
        },
    },
    "media": {
        "icon": "🎵",
        "label": "多媒体",
        "apps": {
            "ffmpeg": {
                "name": "ffmpeg", "display": "FFmpeg",
                "desc": "音视频处理终极工具，转码/剪辑/提取无所不能",
                "category": "media", "tags": ["音视频", "转码"],
                "popularity": 92, "homepage": "https://ffmpeg.org",
                "deps": [],
            },
            "imagemagick": {
                "name": "imagemagick", "display": "ImageMagick",
                "desc": "图片处理工具集，格式转换/缩放/滤镜",
                "category": "media", "tags": ["图片", "处理"],
                "popularity": 78, "homepage": "https://imagemagick.org",
                "deps": [],
            },
            "mpv": {
                "name": "mpv", "display": "MPV",
                "desc": "轻量级命令行媒体播放器",
                "category": "media", "tags": ["播放器", "视频"],
                "popularity": 80, "homepage": "https://mpv.io",
                "deps": [],
            },
        },
    },
    "security": {
        "icon": "🔒",
        "label": "安全工具",
        "apps": {
            "gnupg": {
                "name": "gnupg", "display": "GnuPG",
                "desc": "GNU 隐私卫士，加密/签名工具",
                "category": "security", "tags": ["加密", "PGP"],
                "popularity": 82, "homepage": "https://gnupg.org",
                "deps": [],
            },
            "fail2ban": {
                "name": "fail2ban", "display": "Fail2Ban",
                "desc": "防暴力破解工具，自动封禁恶意IP",
                "category": "security", "tags": ["安全", "防护"],
                "popularity": 75, "homepage": "https://www.fail2ban.org",
                "deps": [],
            },
        },
    },
    "fun": {
        "icon": "🎮",
        "label": "趣味娱乐",
        "apps": {
            "cowsay": {
                "name": "cowsay", "display": "Cowsay",
                "desc": "让牛说话的命令行工具 🐄",
                "category": "fun", "tags": ["趣味", "终端"],
                "popularity": 65, "homepage": "",
                "deps": [],
            },
            "figlet": {
                "name": "figlet", "display": "Figlet",
                "desc": "将文字变成大号 ASCII 艺术字",
                "category": "fun", "tags": ["艺术字", "装逼"],
                "popularity": 60, "homepage": "",
                "deps": [],
            },
            "sl": {
                "name": "sl", "display": "SL (Steam Locomotive)",
                "desc": "输错 ls 时跑过一辆火车 🚂",
                "category": "fun", "tags": ["火车", "恶搞"],
                "popularity": 55, "homepage": "",
                "deps": [],
            },
            "fortune": {
                "name": "fortune", "display": "Fortune",
                "desc": "随机显示一句名人名言或笑话",
                "category": "fun", "tags": ["名言", "随机"],
                "popularity": 58, "homepage": "",
                "deps": [],
            },
            "lolcat": {
                "name": "lolcat", "display": "Lolcat",
                "desc": "给文字加上彩虹色 🌈",
                "category": "fun", "tags": ["彩虹", "炫酷"],
                "popularity": 62, "homepage": "",
                "deps": [],
            },
        },
    },
}

# === 评分系统 ===

def load_ratings() -> Dict[str, dict]:
    try:
        with open(RATINGS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_ratings(ratings: dict):
    try:
        STORE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = RATINGS_FILE.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(ratings, f, indent=2)
        os.replace(tmp, RATINGS_FILE)
    except PermissionError:
        pass

def rate_app(app_name: str, stars: int, comment: str = "", user: str = "anonymous"):
    """给应用评分 (1-5 星)"""
    if not 1 <= stars <= 5:
        raise ValueError("评分必须是 1-5")
    ratings = load_ratings()
    if app_name not in ratings:
        ratings[app_name] = {"ratings": [], "avg": 0, "count": 0}
    ratings[app_name]["ratings"].append({
        "user": user, "stars": stars, "comment": comment,
        "time": time.time(),
    })
    # 重算平均
    all_stars = [r["stars"] for r in ratings[app_name]["ratings"]]
    ratings[app_name]["avg"] = round(sum(all_stars) / len(all_stars), 1)
    ratings[app_name]["count"] = len(all_stars)
    save_ratings(ratings)
    return ratings[app_name]["avg"]

def get_rating(app_name: str) -> dict:
    ratings = load_ratings()
    if app_name not in ratings:
        return {"avg": 0, "count": 0, "ratings": []}
    return ratings[app_name]

# === 自定义应用集 ===

def load_custom() -> Dict[str, dict]:
    try:
        with open(CUSTOM_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_custom(data: dict):
    try:
        STORE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CUSTOM_FILE.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, CUSTOM_FILE)
    except PermissionError:
        pass

def add_custom(name: str, packages: List[str], desc: str = "",
               category: str = "custom") -> dict:
    """添加自定义应用集"""
    customs = load_custom()
    customs[name] = {
        "name": name, "packages": packages, "desc": desc,
        "category": category, "time": time.time(),
    }
    save_custom(customs)
    return customs[name]

def remove_custom(name: str) -> bool:
    customs = load_custom()
    if name in customs:
        del customs[name]
        save_custom(customs)
        return True
    return False

# === 查询接口 ===

def get_all_apps() -> Dict[str, dict]:
    """获取所有应用（含自定义）"""
    all_apps = {}
    for cat_key, cat_data in BUILTIN_APPS.items():
        for app_key, app_data in cat_data["apps"].items():
            all_apps[app_key] = app_data

    customs = load_custom()
    for name, data in customs.items():
        all_apps[name] = {
            "name": name, "display": name,
            "desc": data.get("desc", "自定义应用集"),
            "category": "custom", "tags": ["自定义"],
            "popularity": 50, "homepage": "",
            "deps": data.get("packages", []),
            "is_custom": True,
        }
    return all_apps

def get_categories() -> List[dict]:
    """获取分类列表"""
    cats = []
    for key, data in BUILTIN_APPS.items():
        cats.append({
            "key": key, "icon": data["icon"], "label": data["label"],
            "count": len(data["apps"]),
        })
    customs = load_custom()
    if customs:
        cats.append({
            "key": "custom", "icon": "📦",
            "label": "自定义", "count": len(customs),
        })
    return cats

def get_apps_by_category(cat: str) -> List[dict]:
    """获取某分类下的应用"""
    if cat == "custom":
        customs = load_custom()
        return [
            {"name": n, "display": n, "desc": d.get("desc", ""),
             "category": "custom", "tags": ["自定义"],
             "popularity": 50, "homepage": ""}
            for n, d in customs.items()
        ]
    if cat in BUILTIN_APPS:
        return [
            {"name": k, **v} for k, v in BUILTIN_APPS[cat]["apps"].items()
        ]
    return []

def get_top_apps(n: int = 10) -> List[dict]:
    """热门排行"""
    all_apps = get_all_apps()
    # 结合评分
    ratings = load_ratings()
    scored = []
    for name, info in all_apps.items():
        pop = info.get("popularity", 0)
        avg = ratings.get(name, {}).get("avg", 0)
        count = ratings.get(name, {}).get("count", 0)
        # 综合分 = 流行度 × 0.6 + 评分 × 20 × 0.4
        score = pop * 0.6 + avg * 20 * 0.4 + min(count, 50) * 0.2
        scored.append({"name": name, "score": score, **info})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:n]

def search_apps(keyword: str, limit: int = 20) -> List[dict]:
    """搜索应用"""
    kw = keyword.lower()
    all_apps = get_all_apps()
    results = []
    for name, info in all_apps.items():
        score = 0
        if kw in name.lower():
            score += 10
        desc = info.get("desc", "").lower()
        if kw in desc:
            score += 5
        for tag in info.get("tags", []):
            if kw in tag.lower():
                score += 3
        if score > 0:
            results.append({"name": name, "score": score, **info})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]

def get_app_detail(name: str) -> Optional[dict]:
    """获取应用详情"""
    all_apps = get_all_apps()
    if name not in all_apps:
        return None
    info = dict(all_apps[name])
    rating = get_rating(name)
    info["rating_avg"] = rating["avg"]
    info["rating_count"] = rating["count"]
    info["ratings"] = rating.get("ratings", [])[-5:]  # 最近5条评论
    return info

# === 确保目录 ===

def ensure_dirs():
    try:
        STORE_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        pass

ensure_dirs()

if __name__ == "__main__":
    print("=== X-Store 应用目录 ===\n")
    cats = get_categories()
    for c in cats:
        print(f"  {c['icon']} {c['label']:<10} ({c['count']} 个应用)")

    print(f"\n=== 热门 TOP 5 ===")
    for a in get_top_apps(5):
        print(f"  ⭐ {a['display']:<20} 流行度:{a['popularity']}")

    print(f"\n=== 搜索 'git' ===")
    for a in search_apps("git"):
        print(f"  {a['display']:<20} {a['desc'][:40]}")

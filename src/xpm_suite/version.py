"""
XPM Suite 统一版本管理
合并 xpm + xstore，版本号统一，功能按版本解锁
"""

VERSION_MAJOR = 3
VERSION_MINOR = 1
VERSION_PATCH = 0
VERSION_SUFFIX = "Add Gui Store Edition"

def get_version_string():
    return f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH} \"Add Gui Store Edition\""

def get_short_version():
    return f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

def get_codename():
    return VERSION_SUFFIX

def get_full_name():
    return "XPM Suite"

def get_version_tuple():
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)

def parse_version(vstr):
    """'3.0' -> (3,0,0); '2.1-0' -> (2,1,0); '3.0-0' -> (3,0,0)"""
    import re
    m = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?(?:[-.](\w+))?", str(vstr))
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))

def version_compare(vstr):
    """返回当前版本与给定版本的比较: 1=更新, 0=相等, -1=更旧"""
    a = get_version_tuple()
    b = parse_version(vstr)
    if a > b: return 1
    if a == b: return 0
    return -1

# 各组件版本（独立但配合主版本）
COMPONENTS = {
    "xpm":        {"version": "3.1.0", "name": "XPM 包管理器"},
    "xstore":     {"version": "3.1.0", "name": "X-Store 应用商店 CLI"},
    "xstore-gui": {"version": "3.1.0", "name": "X-Store 图形界面"},
    "downloader": {"version": "3.1.0", "name": "多线程下载器"},
    "formats":    {"version": "3.1.0", "name": "包格式引擎(deb/oil)"},
    "triggers":   {"version": "3.1.0", "name": "触发器引擎"},
    "transaction":{"version": "3.1.0", "name": "事务安装引擎"},
    "auth":       {"version": "3.1.0", "name": "PAM 认证模块"},
    "self_update":{"version": "3.1.0", "name": "自更新引擎"},
    "elevate":    {"version": "3.1.0", "name": "提权包装器"},
}

def get_component_version(name):
    return COMPONENTS.get(name, {}).get("version", "0.0.0")

def get_banner():
    return f"""╔════════════════════════════════════════════╗
║   XPM Suite v{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}              ║
║   "{VERSION_SUFFIX}"         ║
║  ┌────────────┬────────────────────────────┐  ║
║  │ xpm        │ 包管理器 v{COMPONENTS['xpm']['version']}           │  ║
║  │ xstore     │ 应用商店 v{COMPONENTS['xstore']['version']}           │  ║
║  │ xstore-gui │ 图形界面 v{COMPONENTS['xstore-gui']['version']}           │  ║
║  │ auth       │ PAM 认证 v{COMPONENTS['auth']['version']}           │  ║
║  │ self-update│ 自更新   v{COMPONENTS['self_update']['version']}           │  ║
║  │ elevate    │ 提权包装 v{COMPONENTS['elevate']['version']}           │  ║
║  └────────────┴────────────────────────────┘  ║
╚════════════════════════════════════════════╝"""

def get_cli_version_line():
    return f'XPM Suite v{get_short_version()} "{VERSION_SUFFIX}"'

def get_store_version_line():
    return f'xstore v{get_short_version()} (XPM Suite "{VERSION_SUFFIX}")'

def get_gui_title():
    return f"XPM Store — {VERSION_SUFFIX}"

"""
XPM Suite 功能开关
版本不达标 → 功能自动禁用 + 友好提示
"""

from .version import get_version_tuple, parse_version, get_version_string

# 功能注册表：每个功能声明最低版本要求
FEATURES = {
    # === xpm 核心 ===
    "basic_install":    {"min": "1.0", "name": "基础安装/卸载",   "essential": True},
    "search":           {"min": "1.0", "name": "搜索包",         "essential": True},
    "update_index":     {"min": "1.0", "name": "更新索引",       "essential": True},
    "arch_detect":      {"min": "2.0", "name": "智能架构探测",   "essential": True},
    "self_update":      {"min": "2.0", "name": "自动更新自身",   "essential": False},
    "verify_deb":       {"min": "2.0", "name": "下载校验(magic)", "essential": True},
    "pure_python_ar":   {"min": "2.0", "name": "纯Python ar解析","essential": True},
    "dep_resolution":   {"min": "2.1", "name": "依赖解析",       "essential": True},
    "mirror_switch":    {"min": "2.2", "name": "镜像自动切换",   "essential": False},
    "chunk_download":   {"min": "2.2", "name": "多线程分块下载", "essential": False},
    "resume_download":  {"min": "2.2", "name": "断点续传",      "essential": False},

    # === 高级包管理 ===
    "transaction":      {"min": "3.0", "name": "事务安装(全成/全回滚)", "essential": True},
    "triggers":         {"min": "3.0", "name": "触发器引擎",    "essential": True},
    "oil_format":       {"min": "3.0", "name": ".oil 原生格式", "essential": False},
    "rollback":         {"min": "3.0", "name": "事务回滚",      "essential": True},
    "snapshot":         {"min": "3.0", "name": "快照/恢复",     "essential": False},
    "lock_priority":    {"min": "3.0", "name": "版本锁定/优先级","essential": False},
    "parallel_install": {"min": "3.1", "name": "并行安装",      "essential": False},

    # === xstore 应用商店 ===
    "xstore_cli":       {"min": "2.5", "name": "应用商店 CLI",  "essential": False},
    "xstore_catalog":   {"min": "2.5", "name": "应用分类浏览",  "essential": False},
    "xstore_ratings":   {"min": "2.5", "name": "评分/评论系统", "essential": False},
    "xstore_custom":    {"min": "2.5", "name": "自定义应用集",  "essential": False},

    # === xstore GUI ===
    "xstore_gui":       {"min": "3.0", "name": "应用商店 GUI",  "essential": False},
    "gui_themes":       {"min": "3.1", "name": "GUI 主题系统",  "essential": False},
    "gui_plugins":      {"min": "4.0", "name": "GUI 插件系统",  "essential": False},

    # === 诊断 ===
    "doctor":           {"min": "2.0", "name": "系统诊断",      "essential": False},
    "speedtest":        {"min": "2.2", "name": "网络测速",      "essential": False},
}

class FeatureError(Exception):
    """功能不可用时抛出"""
    pass

def check(feature: str, silent=False):
    """
    检查功能是否可用。
    返回 True/False。非 essential 功能不可用只警告；essential 功能不可用抛异常。
    """
    if feature not in FEATURES:
        if not silent:
            print(f"  ⚠️ 未知功能: {feature}")
        return False

    info = FEATURES[feature]
    current = get_version_tuple()
    required = parse_version(info["min"])

    if current >= required:
        return True

    msg = (f"  ⚠️ [{feature}] {info['name']} 需要 v{info['min']}+，"
           f"当前 v{get_version_string()}，该功能不可用")
    if not silent:
        print(msg)

    if info.get("essential"):
        raise FeatureError(f"{info['name']} 是核心功能，需要升级到 v{info['min']}+")
    return False

def require(feature: str):
    """必须可用的功能，不满足直接抛异常"""
    if not check(feature):
        info = FEATURES.get(feature, {})
        raise FeatureError(f"{info.get('name', feature)} 需要 v{info.get('min','?')}+")

def list_features():
    """列出所有功能及其状态"""
    current = get_version_tuple()
    print(f"  XPM Suite v{get_version_string()}")
    print(f"  {'功能':<28}{'最低版本':<12}{'状态':<8}{'必需'}")
    print(f"  {'─'*60}")
    for name, info in sorted(FEATURES.items(), key=lambda x: x[1]["min"]):
        required = parse_version(info["min"])
        ok = "✅" if current >= required else "❌"
        ess = "★" if info.get("essential") else " "
        print(f"  {info['name']:<26}{info['min']:<12}{ok:<8}{ess}")

def disabled_features():
    """返回当前版本不可用的功能列表"""
    current = get_version_tuple()
    return [name for name, info in FEATURES.items()
            if parse_version(info["min"]) > current]

# 初始化时打印版本横幅（仅当直接运行时）
if __name__ == "__main__":
    from .version import get_banner
    print(get_banner())
    print()
    list_features()

"""
X-Store CLI - 应用商店命令行
"""

import sys, os
from .. import check, require, get_version_string
from ..store import (
    get_categories, get_apps_by_category, get_top_apps,
    search_apps, get_app_detail, rate_app, get_rating,
    add_custom, remove_custom, get_all_apps,
)
from ..core.installer import get_engine

# === 输出工具 ===

def _stars(n: float) -> str:
    full = int(n)
    half = 1 if n - full >= 0.5 else 0
    return "★" * full + "☆" * (5 - full - half) + f" {n:.1f}"

def _bar(pct: float, width: int = 20) -> str:
    filled = int(width * pct / 100)
    return "█" * filled + "░" * (width - filled)

def _format_size(n: int) -> str:
    for unit in ["B","KB","MB","GB"]:
        if n < 1024: return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"

# === 命令 ===

def cmd_browse(args=None):
    """浏览应用分类"""
    check("xstore_catalog", silent=True)
    cats = get_categories()
    print(f"\n  🏪 X-Store 应用目录\n")
    for c in cats:
        print(f"  {c['icon']} {c['label']:<10} {c['count']:>3} 个应用")
    print(f"\n  使用 'xstore list <分类>' 查看详情")
    print(f"  使用 'xstore top' 查看热门排行")

def cmd_list(args):
    """列出某分类的应用"""
    check("xstore_catalog", silent=True)
    if not args:
        print("用法: xstore list <分类>")
        print("分类: system / dev / network / media / security / fun / custom")
        return
    cat = args[0]
    apps = get_apps_by_category(cat)
    if not apps:
        print(f"  ⚠️ 分类 '{cat}' 不存在或为空")
        return
    cat_icons = {"system":"⚙️","dev":"💻","network":"🌐",
                 "media":"🎵","security":"🔒","fun":"🎮","custom":"📦"}
    icon = cat_icons.get(cat, "📦")
    print(f"\n  {icon} {cat} 分类应用:\n")
    for a in apps:
        rating = get_rating(a["name"])
        avg = rating.get("avg", 0)
        star_str = _stars(avg) if avg > 0 else "☆☆☆☆☆ 未评分"
        print(f"  • {a['display']:<20} {star_str}")
        print(f"    {a.get('desc','')[:60]}")
        deps = a.get("deps", a.get("packages", []))
        if deps:
            print(f"    包含: {', '.join(deps[:5])}")
        print()

def cmd_search(args):
    """搜索应用"""
    check("xstore_catalog", silent=True)
    if not args:
        print("用法: xstore search <关键词>")
        return
    kw = " ".join(args)
    results = search_apps(kw, limit=15)
    if not results:
        print(f"  🔍 没有找到包含 '{kw}' 的应用")
        return
    print(f"\n  🔍 搜索 '{kw}' 的结果 ({len(results)}个):\n")
    for a in results:
        print(f"  • {a['display']:<20} [{a.get('category','')}]")
        print(f"    {a.get('desc','')[:60]}")

def cmd_top(args):
    """热门排行"""
    check("xstore_catalog", silent=True)
    n = 10
    if args and args[0].isdigit():
        n = int(args[0])
    tops = get_top_apps(n)
    print(f"\n  🔥 热门应用 TOP {n}\n")
    for i, a in enumerate(tops, 1):
        rating = get_rating(a["name"])
        avg = rating.get("avg", 0)
        pop = a.get("popularity", 0)
        print(f"  {i:>2}. {a['display']:<20} {_stars(avg) if avg>0 else '☆☆☆☆☆':<12} "
              f"流行度 {_bar(pop)} {pop}")

def cmd_info(args):
    """应用详情"""
    check("xstore_catalog", silent=True)
    if not args:
        print("用法: xstore info <应用名>")
        return
    name = args[0]
    detail = get_app_detail(name)
    if not detail:
        print(f"  ⚠️ 找不到应用: {name}")
        return

    print(f"\n  📦 {detail.get('display', name)}")
    print(f"  {'─'*50}")
    print(f"  描述: {detail.get('desc','')}")
    print(f"  分类: {detail.get('category','')}")
    if detail.get("homepage"):
        print(f"  主页: {detail['homepage']}")
    if detail.get("deps"):
        print(f"  依赖: {', '.join(detail['deps'])}")
    elif detail.get("packages"):
        print(f"  包含: {', '.join(detail['packages'])}")

    avg = detail.get("rating_avg", 0)
    cnt = detail.get("rating_count", 0)
    if cnt > 0:
        print(f"  评分: {_stars(avg)} ({cnt} 条评论)")
    else:
        print(f"  评分: 暂无评分")

    if detail.get("ratings"):
        print(f"\n  最近评论:")
        for r in detail["ratings"]:
            print(f"    {_stars(r['stars'])} {r.get('comment','')[:40]}")

def cmd_install(args):
    """安装应用（调用 xpm）"""
    check("xstore_catalog", silent=True)
    if not args:
        print("用法: xstore install <应用名>")
        return
    name = args[0]

    # 查应用
    detail = get_app_detail(name)
    if not detail:
        print(f"  ⚠️ 找不到应用: {name}")
        return

    # 获取依赖包列表
    deps = detail.get("deps", detail.get("packages", []))
    if not deps:
        deps = [name]  # 单包

    print(f"  📦 安装 {detail.get('display', name)}")
    print(f"  包含: {', '.join(deps)}")

    # 调用 xpm 安装
    eng = get_engine()
    for pkg in deps:
        try:
            eng.install(pkg)
        except Exception as e:
            print(f"  ❌ {pkg} 安装失败: {e}")
            return

    print(f"  ✅ {detail.get('display', name)} 安装完成！")

def cmd_remove(args):
    """卸载应用"""
    check("xstore_catalog", silent=True)
    if not args:
        print("用法: xstore remove <应用名>")
        return
    name = args[0]
    detail = get_app_detail(name)
    deps = detail.get("deps", detail.get("packages", [])) if detail else [name]

    eng = get_engine()
    for pkg in deps:
        try:
            eng.remove(pkg)
        except Exception as e:
            print(f"  ⚠️ {pkg}: {e}")

def cmd_rate(args):
    """评分"""
    check("xstore_ratings", silent=True)
    if len(args) < 2:
        print("用法: xstore rate <应用名> <1-5星> [评论]")
        return 1
    name = args[0]
    try:
        stars = int(args[1])
    except ValueError:
        print("  ⚠️ 评分必须是 1-5 的整数")
        return 1
    comment = " ".join(args[2:]) if len(args) > 2 else ""
    try:
        avg = rate_app(name, stars, comment)
        print(f"  ✅ 已评分 {_stars(stars)}  {name} 当前均分: {avg}")
    except ValueError as e:
        print(f"  ❌ {e}")
        return 1
    return 0

def cmd_installed(args):
    """已安装应用"""
    check("xstore_catalog", silent=True)
    from ..core.statusdb import get_db
    db = get_db()
    installed = db.installed_packages()
    if not installed:
        print("  📭 尚未安装任何应用")
        return
    print(f"\n  📦 已安装 ({len(installed)} 个)\n")
    for p in sorted(installed, key=lambda x: x.name):
        print(f"  • {p.name:<25} {p.version:<15} [{p.arch}] {p.source_format}")

def cmd_add(args):
    """添加自定义应用集"""
    check("xstore_custom", silent=True)
    if len(args) < 2:
        print("用法: xstore add <名称> <包1,包2,包3> [描述]")
        return
    name = args[0]
    packages = [p.strip() for p in args[1].split(",")]
    desc = " ".join(args[2:]) if len(args) > 2 else ""
    add_custom(name, packages, desc, "custom")
    print(f"  ✅ 自定义应用 '{name}' 已添加")
    print(f"    包含: {', '.join(packages)}")

def cmd_remove_custom(args):
    """删除自定义应用集"""
    check("xstore_custom", silent=True)
    if not args:
        print("用法: xstore remove-custom <名称>")
        return
    if remove_custom(args[0]):
        print(f"  ✅ 已删除 '{args[0]}'")
    else:
        print(f"  ⚠️ 找不到 '{args[0]}'")

def cmd_history(args):
    """下载/安装历史"""
    hist_file = "/var/cache/xpm/download_history.json"
    if not os.path.exists(hist_file):
        print("  📭 暂无历史记录")
        return
    import json
    with open(hist_file) as f:
        history = json.load(f)
    print(f"\n  📋 最近下载 ({len(history)} 条)\n")
    for h in history[-10:]:
        import time
        ts = time.strftime("%m-%d %H:%M", time.localtime(h.get("time", 0)))
        print(f"  {ts}  {h.get('mirror',''):<12} {os.path.basename(h.get('dest',''))}")

# === 主入口 ===

COMMANDS = {
    "browse":    (cmd_browse,     "浏览应用分类"),
    "list":      (cmd_list,       "列出分类下的应用"),
    "search":    (cmd_search,     "搜索应用"),
    "top":       (cmd_top,        "热门排行"),
    "info":      (cmd_info,       "应用详情"),
    "install":   (cmd_install,    "安装应用"),
    "remove":    (cmd_remove,     "卸载应用"),
    "rate":      (cmd_rate,       "评分(1-5星)"),
    "installed": (cmd_installed,  "已安装应用"),
    "add":       (cmd_add,        "添加自定义应用集"),
    "remove-custom": (cmd_remove_custom, "删除自定义应用集"),
    "history":   (cmd_history,    "下载历史"),
}

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if not argv or argv[0] in ("-h", "--help", "help"):
        _print_help()
        return 0

    cmd = argv[0]
    args = argv[1:]

    if cmd == "version":
        print(f"X-Store (xstore) - XPM Suite {get_version_string()}")
        return 0

    if cmd not in COMMANDS:
        print(f"  ⚠️ 未知命令: {cmd}")
        _print_help()
        return 1

    func, _ = COMMANDS[cmd]
    try:
        rc = func(args)
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return 1
    return rc if rc is not None else 0

def _print_help():
    print(f"\n  🏪 X-Store - XPM Suite 应用商店\n")
    print(f"  用法: xstore <命令> [参数...]\n")
    for name, (_, desc) in COMMANDS.items():
        print(f"  {name:<15} {desc}")
    print(f"  {'version':<15} 显示版本")
    print(f"\n  示例:")
    print(f"    xstore browse")
    print(f"    xstore search htop")
    print(f"    xstore info htop")
    print(f"    xstore install htop")
    print(f"    xstore rate htop 5 太好用了")
    print(f"    xstore add mydev git,vim,python3 开发环境")

if __name__ == "__main__":
    sys.exit(main())

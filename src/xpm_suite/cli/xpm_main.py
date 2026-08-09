"""
XPM Suite 主命令行入口 (xpm)
整合: 包管理 + 系统诊断 + 版本管理 + 功能开关
"""

import sys, os, json, time
from typing import List, Optional

from .. import (
    get_version_string, list_features, disabled_features,
    check, require, FEATURES,
)
from ..core.config import (
    detect_architecture, get_arch, set_arch, load_config,
    get_suite,
)
from ..core.statusdb import (
    StatusDB, get_db, create_snapshot, list_snapshots,
    restore_snapshot,
)
from ..core.installer import get_engine, InstallError, DependencyError
from ..core.downloader import (
    get_mirror_manager, measure_all_mirrors, speedtest,
)
from ..core.transaction import Transaction
from ..store import (
    get_categories, get_apps_by_category, get_top_apps,
    search_apps, get_app_detail, get_all_apps,
)

# === 输出工具 ===

def _ok(msg): print(f"  ✅ {msg}")
def _err(msg): print(f"  ❌ {msg}")
def _warn(msg): print(f"  ⚠️  {msg}")
def _info(msg): print(f"  ℹ️  {msg}")
def _bar(pct, w=20): return "█"*int(w*pct/100)+"░"*(w-int(w*pct/100))
def _format_size(n): 
    for u in ["B","KB","MB","GB"]:
        if n<1024: return f"{n:.1f}{u}"
        n/=1024
    return f"{n:.1f}TB"

# === 命令: 版本/信息 ===

def cmd_version(args=None):
    from ..version import get_banner
    print(get_banner())

def cmd_features(args=None):
    """列出所有功能及状态"""
    list_features()
    disabled = disabled_features()
    if disabled:
        _warn(f"不可用功能({len(disabled)}): {', '.join(disabled)}")

def cmd_arch(args=None):
    """显示/设置架构"""
    if args and args[0] in ("set", "switch"):
        if len(args) < 2:
            _err("用法: xpm arch set <arm64|amd64|...>")
            return 1
        try:
            new = set_arch(args[1])
            _ok(f"架构已切换为: {new}")
        except ValueError as e:
            _err(str(e))
            return 1
        return 0

    arch = get_arch()
    cfg = load_config()
    source = cfg.get("arch_source", "未知")
    print(f"  当前架构: {arch}")
    print(f"  探测来源: {source}")
    print(f"  可用: xpm arch set <arch> 切换")
    return 0

# === 命令: 索引/搜索 ===

def cmd_update(args=None):
    """更新索引"""
    require("update_index")
    eng = get_engine()
    _info("正在更新索引...")
    try:
        eng.update_index(progress_cb=lambda c,t,n: print(f"  [{c}/{t}] {n}"))
        total = len(eng.index.packages)
        _ok(f"索引更新完成，共 {total} 个包")
    except Exception as e:
        _err(f"更新失败: {e}")
        return 1
    return 0

def cmd_search(args):
    """搜索包"""
    if not args:
        _err("用法: xpm search <关键词>")
        return 1
    kw = " ".join(args)
    eng = get_engine()
    if not eng.index.packages:
        _info("索引为空，先运行: xpm update")
        return 1
    results = eng.search(kw, limit=20)
    if not results:
        _warn(f"没有找到包含 '{kw}' 的包")
        return 0
    print(f"\n  🔍 搜索 '{kw}' 的结果 ({len(results)}个):\n")
    for r in results:
        print(f"  • {r['name']:<28} {r.get('version',''):<14} {r.get('description','')[:45]}")
    return 0

def cmd_info(args):
    """包详情"""
    if not args:
        _err("用法: xpm info <包名>")
        return 1
    name = args[0]
    eng = get_engine()
    info = eng.index.get_info(name)
    if not info:
        _warn(f"索引中找不到: {name}")
        return 1
    print(f"\n  📦 {info.get('Package','')}")
    print(f"  {'─'*50}")
    for k in ["Version","Architecture","Section","Priority","Installed-Size"]:
        v = info.get(k,"")
        if v: print(f"  {k:<18} {v}")
    deps = info.get("Depends","")
    if deps: print(f"  Depends             {deps[:80]}")
    desc = info.get("Description","").split("\n")
    print(f"\n  {desc[0]}")
    for line in desc[1:]:
        if line.strip(): print(f"  {line.strip()}")
    return 0

# === 命令: 安装/卸载 ===

def cmd_install(args):
    """安装包"""
    if not args:
        _err("用法: xpm install <包名> [包名2 ...]")
        return 1
    eng = get_engine()
    for name in args:
        _info(f"安装 {name}...")
        try:
            ok = eng.install(name)
            if ok: _ok(f"{name} 安装完成")
        except InstallError as e:
            _err(f"{name}: {e}")
            return 1
        except DependencyError as e:
            _err(f"依赖错误: {e}")
            return 1
    return 0

def cmd_remove(args):
    """卸载包"""
    if not args:
        _err("用法: xpm remove <包名> [--purge]")
        return 1
    purge = "--purge" in args
    names = [a for a in args if not a.startswith("--")]
    eng = get_engine()
    for name in names:
        _info(f"卸载 {name}{' (purge)' if purge else ''}...")
        ok = eng.remove(name, purge=purge)
        if ok: _ok(f"{name} 已卸载")
    return 0

def cmd_autoremove(args=None):
    """自动移除不再需要的依赖"""
    eng = get_engine()
    to_remove = eng.autoremove()
    if not to_remove:
        _info("没有可自动移除的包")
        return 0
    _warn(f"将移除 {len(to_remove)} 个不再需要的包:")
    for n in to_remove:
        print(f"  • {n}")
    if input("  确认? [y/N] ").lower() == "y":
        for n in to_remove:
            eng.remove(n)
        _ok("清理完成")
    return 0

# === 命令: 查询 ===

def cmd_list(args=None):
    """列出已安装包"""
    db = get_db()
    pkgs = db.installed_packages()
    if not pkgs:
        _info("尚未安装任何包")
        return 0
    print(f"\n  📦 已安装 ({len(pkgs)} 个)\n")
    # 按格式分组
    by_fmt = {}
    for p in sorted(pkgs, key=lambda x: x.name):
        by_fmt.setdefault(p.source_format, []).append(p)
    for fmt, plist in sorted(by_fmt.items()):
        icon = "📦" if fmt == "deb" else "🛢️"
        print(f"  {icon} [{fmt}] ({len(plist)}个)")
        for p in plist:
            lock = "🔒" if p.locked else "  "
            print(f"    {lock} {p.name:<28} {p.version:<14} [{p.arch}]")
    return 0

def cmd_files(args):
    """列出包安装的文件"""
    if not args:
        _err("用法: xpm files <包名>")
        return 1
    db = get_db()
    files = db.get_files(args[0])
    if not files:
        _warn(f"{args[0]} 未安装或无文件记录")
        return 1
    print(f"  📁 {args[0]} ({len(files)} 个文件):")
    for f in sorted(files)[:100]:
        print(f"    {f}")
    if len(files) > 100:
        print(f"    ... 还有 {len(files)-100} 个文件")
    return 0

def cmd_verify(args):
    """验证包完整性"""
    if not args:
        # 验证所有
        db = get_db()
        pkgs = db.installed_packages()
        ok_count = 0
        for p in pkgs:
            missing = 0
            for f in p.files[:20]:  # 抽样
                full = "/" + f
                if not os.path.exists(full):
                    missing += 1
            status = "✅" if missing == 0 else "⚠️"
            if missing == 0: ok_count += 1
            else: print(f"  {status} {p.name}: {missing} 文件缺失")
        _ok(f"{ok_count}/{len(pkgs)} 包验证通过")
    return 0

def cmd_owns(args):
    """查找文件属于哪个包"""
    if not args:
        _err("用法: xpm owns <文件路径>")
        return 1
    target = args[0].lstrip("/")
    db = get_db()
    for p in db.installed_packages():
        for f in p.files:
            if f == target or f.endswith("/"+target):
                print(f"  📦 {p.name} ({p.version})")
                return 0
    _warn(f"没有包拥有: {target}")
    return 1

# === 命令: 锁定/优先级 ===

def cmd_lock(args):
    """锁定包版本"""
    if not args:
        db = get_db()
        locked = [p for p in db.installed_packages() if p.locked]
        if not locked:
            _info("没有锁定的包")
            return 0
        print("  🔒 已锁定:")
        for p in locked:
            print(f"    {p.name} {p.version}")
        return 0
    db = get_db()
    for name in args:
        db.lock(name)
    _ok(f"已锁定: {', '.join(args)}")
    return 0

def cmd_unlock(args):
    if not args:
        _err("用法: xpm unlock <包名>")
        return 1
    db = get_db()
    for name in args:
        db.unlock(name)
    _ok(f"已解锁: {', '.join(args)}")
    return 0

# === 命令: 快照 ===

def cmd_snapshot(args):
    """创建/列出/恢复快照"""
    if args and args[0] == "list":
        snaps = list_snapshots()
        if not snaps:
            _info("没有快照")
            return 0
        for s in snaps:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(s.get("time",0)))
            print(f"  📸 {s['id']:<25} {ts} ({s.get('packages',0)} 包)")
        return 0
    if args and args[0] == "restore":
        if len(args) < 2:
            _err("用法: xpm snapshot restore <id>")
            return 1
        if restore_snapshot(args[1]):
            _ok(f"已恢复快照: {args[1]}")
            return 0
        _err(f"快照不存在: {args[1]}")
        return 1
    # 创建
    tag = args[0] if args else ""
    sid = create_snapshot(tag)
    _ok(f"快照已创建: {sid}")
    return 0

# === 命令: 清理 ===

def cmd_clean(args=None):
    """清理缓存"""
    cache = "/var/cache/xpm"
    if not os.path.exists(cache):
        _info("缓存目录为空")
        return 0
    total = 0
    for f in os.listdir(cache):
        fp = os.path.join(cache, f)
        if os.path.isfile(fp):
            total += os.path.getsize(fp)
            os.remove(fp)
    _ok(f"已清理 {_format_size(total)}")
    return 0

def cmd_orphan(args=None):
    """查找孤儿包"""
    eng = get_engine()
    orphans = eng.autoremove()
    if not orphans:
        _info("没有孤儿包")
        return 0
    print(f"  🔍 发现 {len(orphans)} 个孤儿包:")
    for n in orphans:
        print(f"    • {n}")
    return 0

def cmd_duplicate(args=None):
    """查找重复文件"""
    db = get_db()
    file_map = {}
    for p in db.installed_packages():
        for f in p.files:
            if f in file_map:
                file_map[f].append(p.name)
            else:
                file_map[f] = [p.name]
    dups = {f: pkgs for f, pkgs in file_map.items() if len(pkgs) > 1}
    if not dups:
        _ok("没有重复文件")
        return 0
    print(f"  ⚠️ 发现 {len(dups)} 个重复文件:")
    for f, pkgs in list(dups.items())[:20]:
        print(f"    {f}: {', '.join(pkgs)}")
    return 0

# === 命令: 诊断 ===

def cmd_doctor(args=None):
    """系统诊断"""
    require("doctor")
    print("  🩺 XPM Suite 系统诊断\n")

    # 版本
    print(f"  📌 版本: {get_version_string()}")

    # 架构
    arch = get_arch()
    print(f"  🏗️  架构: {arch}")

    # 目录
    from ..core.config import CONFIG_DIR, CACHE_DIR, STATE_DIR
    for d, label in [(CONFIG_DIR,"配置"), (CACHE_DIR,"缓存"), (STATE_DIR,"状态")]:
        ok = os.path.exists(d)
        icon = "✅" if ok else "⚠️"
        print(f"  {icon} {label}目录: {d} {'存在' if ok else '不存在(将自动创建)'}")

    # 依赖工具
    import shutil
    for tool in ["dpkg","gzip","tar","curl"]:
        path = shutil.which(tool)
        icon = "✅" if path else "⚠️"
        print(f"  {icon} {tool:<12} {path or '未找到(可选)'}")

    # 网络
    print(f"\n  🌐 网络测试:")
    try:
        import urllib.request
        with urllib.request.urlopen("https://mirrors.tuna.tsinghua.edu.cn", timeout=5) as r:
            _ok(f"清华镜像可达 (HTTP {r.status})")
    except Exception as e:
        _warn(f"清华镜像不可达: {e}")

    # 索引
    eng = get_engine()
    if eng.index.packages:
        _ok(f"索引已加载 ({len(eng.index.packages)} 包)")
    else:
        _warn("索引为空，建议运行: xpm update")

    # 已安装
    db = get_db()
    cnt = db.count()
    _ok(f"已安装 {cnt} 个包")

    return 0

# === 命令: 网络 ===

def cmd_mirrors(args=None):
    """测速所有镜像"""
    mgr = get_mirror_manager()
    print("  🌐 镜像测速...\n")
    results = measure_all_mirrors()
    for r in results:
        if "error" in r:
            print(f"  ❌ {r['mirror']:<15} {r['error']}")
        else:
            print(f"  ✅ {r['mirror']:<15} {r['latency_ms']:>8.1f}ms  "
                  f"{r['download_mbps']:>8.2f} Mbps")
    return 0

def cmd_speedtest(args):
    """测速指定路径"""
    path = args[0] if args else "dists/trixie/Release"
    result = speedtest(path)
    if "error" in result:
        _err(result["error"])
        return 1
    _ok(f"{result['mirror']}: {result['latency_ms']}ms, "
        f"{result['download_mbps']} Mbps")
    return 0

# === 命令: 自更新 ===

def cmd_self_update(args=None):
    """从 GitHub 下载最新版本"""
    require("self_update")
    import urllib.request
    _info("检查最新版本...")
    url = "https://api.github.com/repos/zizhao114514/xpm/releases/latest"
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"XPM"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        latest = data.get("tag_name","?")
        print(f"  最新版本: {latest}")
        # 下载 .deb
        assets = data.get("assets", [])
        for a in assets:
            if a["name"].endswith(".deb"):
                dl_url = a["browser_download_url"]
                _info(f"下载 {a['name']}...")
                dest = f"/var/cache/xpm/{a['name']}"
                urllib.request.urlretrieve(dl_url, dest)
                _ok(f"已下载: {dest}")
                _info("安装: dpkg -i " + dest)
                os.system(f"dpkg -i {dest}")
                return 0
        _warn("Release 中没有 .deb 文件")
        return 1
    except Exception as e:
        _err(f"更新失败: {e}")
        return 1

# === 命令: 触发器 ===

def cmd_triggers(args=None):
    """查看触发器状态"""
    require("triggers")
    from ..core.triggers import get_engine as get_trig
    eng = get_trig()
    status = eng.get_status()
    print(f"  🔗 触发器状态:")
    print(f"     Pending 数量: {status['pending_count']}")
    print(f"     已注册兴趣:  {status['registered_interests']} 条规则")
    if status['pending_triggers']:
        print(f"     Pending 列表: {', '.join(status['pending_triggers'])}")
    return 0

# === 命令: 历史 ===

def cmd_history(args=None):
    """下载/安装历史"""
    hist_file = "/var/cache/xpm/download_history.json"
    if not os.path.exists(hist_file):
        _info("暂无历史记录")
        return 0
    with open(hist_file) as f:
        history = json.load(f)
    print(f"\n  📋 最近下载 ({len(history)} 条)\n")
    for h in history[-15:]:
        ts = time.strftime("%m-%d %H:%M", time.localtime(h.get("time",0)))
        size = _format_size(h.get("size",0))
        print(f"  {ts}  {h.get('mirror',''):<12} {os.path.basename(h.get('dest','')):<35} {size}")
    return 0

# === 命令: 锁定列表 ===

def cmd_locks(args=None):
    return cmd_lock([])

# === 命令: 设置优先级 ===

def cmd_set_priority(args):
    _warn("优先级功能在 v3.1+ 提供完整支持")
    _info("当前可通过 xpm lock <pkg> 锁定版本")
    return 0

# === 主路由 ===

COMMANDS = {
    "version":      (cmd_version,      "显示版本信息"),
    "features":     (cmd_features,     "列出所有功能及状态"),
    "arch":         (cmd_arch,         "显示/切换架构"),
    "update":       (cmd_update,       "更新软件源索引"),
    "search":       (cmd_search,       "搜索软件包"),
    "info":         (cmd_info,         "包详情"),
    "install":      (cmd_install,      "安装软件包"),
    "remove":       (cmd_remove,       "卸载软件包"),
    "autoremove":   (cmd_autoremove,   "自动移除无用依赖"),
    "list":         (cmd_list,         "列出已安装包"),
    "files":        (cmd_files,        "列出包的文件"),
    "verify":       (cmd_verify,       "验证包完整性"),
    "owns":         (cmd_owns,         "查找文件属于哪个包"),
    "lock":         (cmd_lock,         "锁定包版本"),
    "unlock":       (cmd_unlock,       "解锁包版本"),
    "locks":        (cmd_locks,        "列出已锁定包"),
    "snapshot":     (cmd_snapshot,     "快照管理"),
    "clean":        (cmd_clean,        "清理缓存"),
    "orphan":       (cmd_orphan,       "查找孤儿包"),
    "duplicate":    (cmd_duplicate,    "查找重复文件"),
    "doctor":       (cmd_doctor,       "系统诊断"),
    "mirrors":      (cmd_mirrors,      "镜像测速"),
    "speedtest":    (cmd_speedtest,    "网络测速"),
    "self-update":  (cmd_self_update,  "更新 XPM 自身"),
    "triggers":     (cmd_triggers,     "触发器状态"),
    "history":      (cmd_history,      "下载历史"),
    "priority":     (cmd_set_priority, "设置包优先级"),
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
        cmd_version()
        return 0

    if cmd not in COMMANDS:
        _err(f"未知命令: {cmd}")
        _print_help()
        return 1

    func, _ = COMMANDS[cmd]
    try:
        return func(args) or 0
    except KeyboardInterrupt:
        print("\n  ⏹️  已取消")
        return 130
    except Exception as e:
        _err(f"内部错误: {e}")
        if os.environ.get("XPM_DEBUG"):
            import traceback
            traceback.print_exc()
        return 1

def _print_help():
    print(f"\n  🏪 XPM Suite {get_version_string()}\n")
    print(f"  用法: xpm <命令> [参数...]\n")
    # 分组显示
    groups = [
        ("信息查询", ["version","features","arch","info","search","list","files","owns","history"]),
        ("包管理",   ["update","install","remove","autoremove","verify"]),
        ("锁定/快照", ["lock","unlock","locks","snapshot","priority"]),
        ("清理",     ["clean","orphan","duplicate"]),
        ("网络",     ["mirrors","speedtest","self-update"]),
        ("系统",     ["doctor","triggers"]),
    ]
    for gname, cmds in groups:
        print(f"  {gname}:")
        for c in cmds:
            if c in COMMANDS:
                func, desc = COMMANDS[c]
                print(f"    {c:<14} {desc}")
    print(f"\n  完整文档: https://github.com/zizhao114514/xpm")

if __name__ == "__main__":
    sys.exit(main())

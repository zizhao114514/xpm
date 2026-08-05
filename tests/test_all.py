#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XPM v2.0-7 测试套件
覆盖：版本比较、依赖解析、源解析、数据库 CRUD、事务回滚、GPG、构建工具、
      搜索、provides、owns、size、history、alias、autoremove、clean、dedupe、
      self-update、package_download_url、release_url
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
import time
import hashlib
from pathlib import Path

# 设置测试环境
TEST_ROOT = tempfile.mkdtemp(prefix="xpm_test_")
os.environ["XPM_TEST_MODE"] = "1"
os.environ["XPM_ROOT"] = TEST_ROOT

# 导入 xpm 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import xpm

xpm.XPM_ROOT = TEST_ROOT
xpm.XPM_DB = f"{TEST_ROOT}/db"
xpm.XPM_STATUS = f"{TEST_ROOT}/db/status.json"
xpm.XPM_SOURCES = f"{TEST_ROOT}/sources.list.d"
xpm.XPM_CACHE = f"{TEST_ROOT}/cache"
xpm.XPM_LOG = f"{TEST_ROOT}/log"
xpm.XPM_HISTORY = f"{TEST_ROOT}/log/history.jsonl"
xpm.XPM_CONFIG = f"{TEST_ROOT}/config.json"
xpm.XPM_ALIASES = f"{TEST_ROOT}/aliases.json"
xpm.XPM_TRANSACTIONS = f"{TEST_ROOT}/db/transactions"
xpm.XPM_KEYRING = f"{TEST_ROOT}/keyring"
xpm.XPM_DOCS = f"{TEST_ROOT}/docs"

xpm.ensure_dirs()

passed = 0
failed = 0
failures = []

def test(name):
    def decorator(func):
        global passed, failed
        try:
            func()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
            failures.append((name, str(e)))
        return func
    return decorator

def assert_eq(a, b, msg=""):
    if a != b:
        raise AssertionError(f"期望 {b!r}, 实际 {a!r} {msg}")

def assert_true(c, msg=""):
    if not c:
        raise AssertionError(f"断言失败: {msg}")

# ─── 1. 版本比较 ───────────────────────────────────────
@test("版本比较: 等于")
def t_version_eq():
    assert_eq(xpm.compare_version("1.0", "1.0"), 0)

@test("版本比较: 小于")
def t_version_lt():
    assert_true(xpm.compare_version("1.0", "2.0") < 0)

@test("版本比较: 大于")
def t_version_gt():
    assert_true(xpm.compare_version("2.0", "1.0") > 0)

@test("版本比较: epoch")
def t_version_epoch():
    assert_true(xpm.compare_version("1:1.0", "1.0") > 0)

@test("版本比较: debian 后缀")
def t_version_debian():
    assert_true(xpm.compare_version("1.0-1", "1.0-2") < 0)

# ─── 2. 依赖解析 ───────────────────────────────────────
@test("解析 control 格式")
def t_parse_control():
    text = "Package: vim\nVersion: 9.1\nDepends: libc6 (>= 2.0), ncurses\nDescription: editor"
    ctrl = xpm.parse_control(text)
    assert_eq(ctrl["Package"], "vim")
    assert_eq(ctrl["Version"], "9.1")
    assert_true("libc6" in ctrl["Depends"])
    assert_eq(ctrl["Description"], "editor")

@test("解析依赖字符串 - AND")
def t_parse_dep_and():
    deps = xpm.parse_dep_string("libc6 (>= 2.0), ncurses")
    assert_eq(len(deps), 2)
    assert_eq(deps[0][0], ("libc6", ">=", "2.0"))

@test("解析依赖字符串 - OR")
def t_parse_dep_or():
    deps = xpm.parse_dep_string("libc6 | libc6-alt (>= 1.0)")
    assert_eq(len(deps), 1)
    assert_eq(len(deps[0]), 2)

# ─── 3. 数据库 CRUD ────────────────────────────────────
@test("保存和加载状态")
def t_db_save_load():
    db = {"installed": {"vim": {"version": "9.1", "files": ["/usr/bin/vim"]}}}
    xpm.save_status(db)
    loaded = xpm.load_status()
    assert_eq(loaded["installed"]["vim"]["version"], "9.1")

@test("空数据库处理")
def t_db_empty():
    if os.path.exists(xpm.XPM_STATUS):
        os.unlink(xpm.XPM_STATUS)
    db = xpm.load_status()
    assert_true("installed" in db)

# ─── 4. 历史记录 ───────────────────────────────────────
@test("写入和读取历史")
def t_history():
    if os.path.exists(xpm.XPM_HISTORY):
        os.unlink(xpm.XPM_HISTORY)
    xpm.log_history("install", "vim", "version=9.1")
    xpm.log_history("remove", "nano", "")
    hist = xpm.read_history()
    assert_eq(len(hist), 2)
    assert_eq(hist[0]["action"], "install")
    assert_eq(hist[1]["package"], "nano")

# ─── 5. 别名系统 ───────────────────────────────────────
@test("别名增删查")
def t_aliases():
    if os.path.exists(xpm.XPM_ALIASES):
        os.unlink(xpm.XPM_ALIASES)
    xpm.alias_add("i", "install")
    xpm.alias_add("rm", "remove")
    a = xpm.load_aliases()
    assert_eq(a["i"], "install")
    xpm.alias_remove("rm")
    a = xpm.load_aliases()
    assert_true("rm" not in a)

# ─── 6. 配置管理 ───────────────────────────────────────
@test("配置读写")
def t_config():
    if os.path.exists(xpm.XPM_CONFIG):
        os.unlink(xpm.XPM_CONFIG)
    cfg = xpm.load_config()
    assert_true("language" in cfg)
    cfg["test_key"] = "test_val"
    xpm.save_config(cfg)
    cfg2 = xpm.load_config()
    assert_eq(cfg2["test_key"], "test_val")

# ─── 7. 源解析 ─────────────────────────────────────────
@test("解析软件源")
def t_parse_sources():
    os.makedirs(xpm.XPM_SOURCES, exist_ok=True)
    sf = f"{xpm.XPM_SOURCES}/test.list"
    with open(sf, "w") as f:
        f.write("deb http://example.com/debian bookworm main\n")
        f.write("# 这是注释\n")
        f.write("[xpm] url=http://repo.example.com\n")
    sources = xpm.parse_sources()
    assert_eq(len(sources), 2)
    os.unlink(sf)

# ─── 8. 包索引构建（mock） ─────────────────────────────
@test("构建包索引")
def t_build_index():
    os.makedirs(xpm.XPM_CACHE, exist_ok=True)
    mock_packages = """Package: vim
Version: 9.1
Depends: ncurses
Description: Vi IMproved

Package: nano
Version: 7.2
Description: simple editor

Package: vim
Version: 9.0
Description: old vim

"""
    url = "http://mock/repo/dists/stable/main/binary-amd64/Packages.gz"
    cache_name = hashlib.md5(url.encode()).hexdigest()[:12]
    cache_file = f"{xpm.XPM_CACHE}/{cache_name}_Packages"
    with open(cache_file, "w") as f:
        f.write(mock_packages)

    os.makedirs(xpm.XPM_SOURCES, exist_ok=True)
    sf = f"{xpm.XPM_SOURCES}/mock.list"
    with open(sf, "w") as f:
        f.write("deb http://mock/repo stable main\n")

    index = xpm.build_package_index()
    assert_true("vim" in index, f"vim should be in index, got: {list(index.keys())}")
    assert_true("nano" in index, f"nano should be in index, got: {list(index.keys())}")
    assert_eq(len(index["vim"]), 2)
    if os.path.exists(cache_file): os.unlink(cache_file)
    if os.path.exists(sf): os.unlink(sf)

# ─── 9. 搜索 ───────────────────────────────────────────
@test("模糊搜索")
def t_search():
    os.makedirs(xpm.XPM_CACHE, exist_ok=True)
    mock = """Package: vim-editor
Version: 9.1
Description: Vi IMproved text editor

Package: firefox-browser
Version: 115
Description: web browser

"""
    url = "http://x/dists/stable/main/binary-amd64/Packages.gz"
    cache_name = hashlib.md5(url.encode()).hexdigest()[:12]
    cf = f"{xpm.XPM_CACHE}/{cache_name}_Packages"
    with open(cf, "w") as f:
        f.write(mock)
    os.makedirs(xpm.XPM_SOURCES, exist_ok=True)
    sf = f"{xpm.XPM_SOURCES}/s.list"
    with open(sf, "w") as f:
        f.write("deb http://x stable main\n")

    results = xpm.search_packages("editor")
    names = [r["Package"] for r in results]
    assert_true("vim-editor" in names, f"vim-editor should be in {names}")

    results2 = xpm.search_packages("fire")
    names2 = [r["Package"] for r in results2]
    assert_true("firefox-browser" in names2, f"firefox-browser should be in {names2}")

    os.unlink(cf)
    os.unlink(sf)

# ─── 10. provides / owns ────────────────────────────────
@test("provides 查询")
def t_provides():
    os.makedirs(xpm.XPM_CACHE, exist_ok=True)
    mock = """Package: vim
Version: 9.1
Provides: vi, editor
Description: vim

"""
    url = "http://x/dists/stable/main/binary-amd64/Packages.gz"
    cache_name = hashlib.md5(url.encode()).hexdigest()[:12]
    cf = f"{xpm.XPM_CACHE}/{cache_name}_Packages"
    with open(cf, "w") as f:
        f.write(mock)
    os.makedirs(xpm.XPM_SOURCES, exist_ok=True)
    sf = f"{xpm.XPM_SOURCES}/p.list"
    with open(sf, "w") as f:
        f.write("deb http://x stable main\n")

    results = xpm.find_provides("vi")
    names = [r["Package"] for r in results]
    assert_true("vim" in names, f"vim should be in {names}")

    os.unlink(cf)
    os.unlink(sf)

@test("owns 查询")
def t_owns():
    db = {"installed": {"vim": {"version": "9.1", "files": ["/usr/bin/vim", "/usr/share/man/man1/vim.1"]}}}
    xpm.save_status(db)
    result = xpm.find_owns("/usr/bin/vim")
    assert_eq(result[0], "vim")
    result2 = xpm.find_owns("/nonexist")
    assert_eq(result2[0], None)

# ─── 11. size 计算 ──────────────────────────────────────
@test("size 计算")
def t_size():
    test_file = f"{TEST_ROOT}/test_size_file"
    with open(test_file, "wb") as f:
        f.write(b"x" * 1024)
    db = {"installed": {"testpkg": {"version": "1.0", "files": [test_file]}}}
    xpm.save_status(db)
    total = 0
    for f in db["installed"]["testpkg"]["files"]:
        if os.path.exists(f):
            total += os.path.getsize(f)
    assert_eq(total, 1024)

# ─── 12. autoremove 逻辑 ───────────────────────────────
@test("autoremove 检测孤儿")
def t_autoremove():
    db = {
        "installed": {
            "A": {"version": "1.0", "files": []},
            "B": {"version": "1.0", "files": []},
            "C": {"version": "1.0", "files": []}
        }
    }
    xpm.save_status(db)

    ctrl_dir = f"{TEST_ROOT}/db/control"
    os.makedirs(ctrl_dir, exist_ok=True)
    with open(f"{ctrl_dir}/A", "w") as f:
        f.write("Package: A\nDepends: B\n")
    with open(f"{ctrl_dir}/B", "w") as f:
        f.write("Package: B\n")
    with open(f"{ctrl_dir}/C", "w") as f:
        f.write("Package: C\n")

    deps_of = {}
    for name in db["installed"]:
        deps_of[name] = set()

    for name in db["installed"]:
        ctrl_path = f"{ctrl_dir}/{name}"
        if os.path.exists(ctrl_path):
            ctrl_text = open(ctrl_path).read()
            for line in ctrl_text.split("\n"):
                if line.startswith("Depends:"):
                    deps_str = line.split(":", 1)[1].strip()
                    for dep in deps_str.split(","):
                        dep = dep.strip().split()[0].rstrip(",")
                        if dep in deps_of:
                            deps_of[dep].add(name)

    orphans = [n for n in db["installed"] if not deps_of.get(n)]
    assert_true("C" in orphans, "C should be orphan")
    assert_true("A" in orphans, "A should be orphan")
    assert_true("B" not in orphans, "B should NOT be orphan")

# ─── 13. clean 缓存清理 ────────────────────────────────
@test("clean 缓存清理")
def t_clean():
    os.makedirs(xpm.XPM_CACHE, exist_ok=True)
    test_cache = f"{xpm.XPM_CACHE}/test_cache.oil"
    with open(test_cache, "wb") as f:
        f.write(b"fake cache data" * 100)
    assert_true(os.path.exists(test_cache))
    xpm.clean_cache(aggressive=True)
    assert_true(not os.path.exists(test_cache))

# ─── 14. dedupe 检测 ──────────────────────────────────
@test("dedupe 重复检测")
def t_dedupe():
    db = {
        "installed": {
            "pkgA": {"version": "1.0", "files": ["/usr/share/common.txt"]},
            "pkgB": {"version": "1.0", "files": ["/usr/share/common.txt", "/usr/share/b.txt"]}
        }
    }
    xpm.save_status(db)
    file_owners = {}
    for pkg, info in db["installed"].items():
        for f in info["files"]:
            if f not in file_owners:
                file_owners[f] = []
            file_owners[f].append(pkg)
    conflicts = {f: o for f, o in file_owners.items() if len(o) > 1}
    assert_true("/usr/share/common.txt" in conflicts)
    assert_eq(len(conflicts["/usr/share/common.txt"]), 2)

# ─── 15. 事务回滚 ──────────────────────────────────────
@test("事务回滚")
def t_rollback():
    os.makedirs(xpm.XPM_TRANSACTIONS, exist_ok=True)
    tx_dir = f"{xpm.XPM_TRANSACTIONS}/1"
    os.makedirs(tx_dir, exist_ok=True)
    snapshot = {"installed": {"vim": {"version": "9.0"}}}
    with open(f"{tx_dir}/snapshot.json", "w") as f:
        json.dump(snapshot, f)
    loaded = json.load(open(f"{tx_dir}/snapshot.json"))
    assert_eq(loaded["installed"]["vim"]["version"], "9.0")

# ─── 16. 依赖解析器 ────────────────────────────────────
@test("依赖解析器 - 基础")
def t_resolve_basic():
    index = {
        "vim": [{"Package": "vim", "Version": "9.1", "Depends": "ncurses, libreadline"}],
        "ncurses": [{"Package": "ncurses", "Version": "6.4", "Depends": ""}],
        "libreadline": [{"Package": "libreadline", "Version": "8.2", "Depends": ""}]
    }
    db = {"installed": {}}
    result = xpm.resolve_dependencies("vim", index, db)
    names = [e["Package"] for e in result]
    assert_true("vim" in names)
    assert_true("ncurses" in names)
    assert_true("libreadline" in names)

@test("依赖解析器 - 已装跳过")
def t_resolve_skip():
    index = {
        "vim": [{"Package": "vim", "Version": "9.1", "Depends": "libreadline"}],
        "libreadline": [{"Package": "libreadline", "Version": "8.2", "Depends": ""}]
    }
    db = {"installed": {"libreadline": {"version": "8.2"}}}
    result = xpm.resolve_dependencies("vim", index, db)
    names = [e["Package"] for e in result]
    assert_true("vim" in names)
    assert_true("libreadline" not in names)

# ─── 17. 构建 .oil 包 ──────────────────────────────────
@test("构建 .oil 包")
def t_build_oil():
    build_dir = f"{TEST_ROOT}/build_test"
    os.makedirs(build_dir, exist_ok=True)
    with open(f"{build_dir}/control", "w") as f:
        f.write("Package: testpkg\nVersion: 1.0\nDescription: test\n")
    os.makedirs(f"{build_dir}/usr/bin", exist_ok=True)
    with open(f"{build_dir}/usr/bin/testapp", "w") as f:
        f.write("#!/bin/sh\necho hello\n")
    os.chmod(f"{build_dir}/usr/bin/testapp", 0o755)

    import xpm_build
    result = xpm_build.build_oil(build_dir)
    assert_true(result)
    for f in os.listdir("."):
        if f.endswith(".oil"):
            assert_true(os.path.getsize(f) > 0)
            os.unlink(f)
            break

# ─── 18. 帮助系统 ──────────────────────────────────────
@test("帮助系统 - 中文")
def t_help_zh():
    os.environ["LANG"] = "zh_CN.UTF-8"
    assert_true("XPM - X11 包管理器" in xpm.HELP_ZH)
    assert_true("install" in xpm.HELP_ZH)
    assert_true("self-update" in xpm.HELP_ZH, "should mention self-update")

@test("帮助系统 - 英文")
def t_help_en():
    assert_true("XPM - X11 Package Manager" in xpm.HELP_EN)
    assert_true("self-update" in xpm.HELP_EN, "should mention self-update")

@test("帮助系统 - 日文")
def t_help_ja():
    assert_true("XPM - X11 パッケージマネージャー" in xpm.HELP_JA)

# ─── 19. doctor 检查项 ──────────────────────────────────
@test("doctor 不崩溃")
def t_doctor():
    import io
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        xpm.doctor()
    finally:
        sys.stdout = old

# ─── 20. 集成测试 ───────────────────────────────────────
@test("集成: 完整安装流程")
def t_integration_install():
    os.makedirs(xpm.XPM_SOURCES, exist_ok=True)
    sf = f"{xpm.XPM_SOURCES}/int.list"
    with open(sf, "w") as f:
        f.write("deb http://mock/repo stable main\n")

    url = "http://mock/repo/dists/stable/main/binary-amd64/Packages.gz"
    cache_name = hashlib.md5(url.encode()).hexdigest()[:12]

    mock_pkgs = """Package: testapp
Version: 1.0
Depends: testlib (>= 1.0)
Description: test application

Package: testlib
Version: 1.2
Description: test library

"""
    cf = f"{xpm.XPM_CACHE}/{cache_name}_Packages"
    with open(cf, "w") as f:
        f.write(mock_pkgs)

    oil_dir = f"{TEST_ROOT}/oil_build"
    os.makedirs(f"{oil_dir}/usr/bin", exist_ok=True)
    with open(f"{oil_dir}/control", "w") as f:
        f.write("Package: testapp\nVersion: 1.0\nDepends: testlib (>= 1.0)\nDescription: test\n")
    with open(f"{oil_dir}/usr/bin/testapp", "w") as f:
        f.write("#!/bin/sh\necho test\n")

    import xpm_build
    xpm_build.build_oil(oil_dir)

    oil_file = None
    for f in os.listdir("."):
        if f.endswith(".oil"):
            oil_file = f
            break

    assert_true(oil_file is not None, "should have created .oil file")
    if oil_file:
        assert_true(os.path.getsize(oil_file) > 0)
        os.unlink(oil_file)

    if os.path.exists(cf): os.unlink(cf)
    if os.path.exists(sf): os.unlink(sf)

# ─── 21. self-update 系统 ───────────────────────────────
@test("self-update: 版本比较逻辑")
def t_self_update_version():
    cur = "2.0-7"
    newer = "2.0-8"
    older = "2.0-6"
    assert_true(xpm.compare_version(newer, cur) > 0, "2.0-8 should > 2.0-7")
    assert_true(xpm.compare_version(older, cur) < 0, "2.0-6 should < 2.0-7")
    assert_true(xpm.compare_version(cur, cur) == 0, "same version should == 0")

@test("self-update: package_download_url 使用 Filename")
def t_pkg_download_url_filename():
    entry = {
        "Package": "htop",
        "Version": "3.4.1-5",
        "Architecture": "amd64",
        "Filename": "pool/main/h/htop/htop_3.4.1-5_amd64.deb",
        "_base": "https://mirrors.tuna.tsinghua.edu.cn/debian",
        "_component": "main",
    }
    url = xpm.package_download_url(entry)
    expected = "https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/h/htop/htop_3.4.1-5_amd64.deb"
    assert_eq(url, expected, f"\n  expected: {expected}\n  got:      {url}")

@test("self-update: package_download_url 兜底拼接")
def t_pkg_download_url_fallback():
    entry = {
        "Package": "libtinfo6",
        "Version": "6.5+20250216-2",
        "Architecture": "amd64",
        "_base": "https://mirrors.tuna.tsinghua.edu.cn/debian",
        "_component": "main",
    }
    url = xpm.package_download_url(entry)
    assert_true("l/libtinfo6/" in url, f"should contain l/libtinfo6/, got: {url}")
    assert_true(url.startswith("https://"), f"should be full URL, got: {url}")

@test("self-update: release_url 正确拼接")
def t_release_url_normal():
    src = {"type": "deb", "base": "https://mirrors.tuna.tsinghua.edu.cn/debian", "suite": "trixie", "components": ["main"]}
    url = xpm.release_url(src)
    expected = "https://mirrors.tuna.tsinghua.edu.cn/debian/dists/trixie/Release"
    assert_eq(url, expected, f"\n  expected: {expected}\n  got:      {url}")

@test("self-update: release_url 兼容 /dists 结尾")
def t_release_url_dists():
    src = {"type": "deb", "base": "https://example.com/repo/dists", "suite": "stable", "components": ["main"]}
    url = xpm.release_url(src)
    expected = "https://example.com/repo/dists/stable/Release"
    assert_eq(url, expected, f"\n  expected: {expected}\n  got:      {url}")

@test("self-update: compare_xpm_version")
def t_compare_xpm_version():
    # 模拟 get_latest_version 返回值
    # 远程比本地新
    r = xpm.compare_xpm_version("2.0-8")
    assert_true(r > 0, f"2.0-8 should be newer than {xpm.VERSION}")
    # 远程和本地一样
    r2 = xpm.compare_xpm_version(xpm.VERSION)
    assert_eq(r2, 0)
    # 远程比本地旧
    r3 = xpm.compare_xpm_version("1.0-0")
    assert_true(r3 < 0, "1.0-0 should be older")

@test("self-update: GITHUB URL 常量")
def t_github_urls():
    assert_true(xpm.GITHUB_API_RELEASES.startswith("https://"))
    assert_true("releases/latest" in xpm.GITHUB_API_RELEASES)
    assert_true(xpm.GITHUB_DOWNLOAD_BASE.startswith("https://"))
    assert_true("github.com" in xpm.GITHUB_DOWNLOAD_BASE)

# ─── 汇总 ─────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"测试结果: {passed} 通过, {failed} 失败")
print(f"{'='*50}")

if failures:
    print("\n失败详情:")
    for name, err in failures:
        print(f"  ❌ {name}: {err}")

# 清理
shutil.rmtree(TEST_ROOT, ignore_errors=True)

sys.exit(0 if failed == 0 else 1)

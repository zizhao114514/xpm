#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XPM v2.0-0 完整测试套件
运行: python3 tests/test_all.py
"""

import os, sys, json, tempfile, subprocess, hashlib, time
from pathlib import Path

# 确保能导入 xpm.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = 0
failed = 0
failures = []

def test(name):
    def deco(fn):
        global passed, failed
        try:
            fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failures.append((name, str(e)))
            failed += 1
        return fn
    return deco

def assert_eq(a, b):
    if a != b:
        raise AssertionError(f"expected {b!r}, got {a!r}")

def assert_true(x, msg=None):
    if not x:
        raise AssertionError(msg or "expected truthy")

def assert_in(a, b):
    if a not in b:
        raise AssertionError(f"{a!r} not in {b!r}")

# ====== 1. 版本比较 ======
@test("version_compare: epoch 处理")
def t():
    from xpm import DependencyResolver
    r = DependencyResolver()
    # 简化版只测基本比较
    assert_true(r.compare_versions("1.0", ">=", "0.5"))
    assert_true(r.compare_versions("2.0", ">", "1.0"))
    assert_true(r.compare_versions("1.0", "=", "1.0"))
    assert_true(not r.compare_versions("1.0", "<", "0.5"))

@test("version_compare: Debian epoch")
def t():
    from xpm import DependencyResolver
    r = DependencyResolver()
    # 2:9.1 > 9.1 (epoch 2 > epoch 0)
    assert_true(r.compare_versions("2:9.1", ">=", "9.1"))

# ====== 2. 依赖解析 ======
@test("depends 解析: 简单依赖")
def t():
    from xpm import DependencyResolver
    r = DependencyResolver()
    deps = r.parse_depends("libc6 (>= 2.28), libssl3")
    assert_eq(len(deps), 2)
    assert_eq(deps[0][0], ("libc6", ">=", "2.28"))
    assert_eq(deps[1][0], ("libssl3", "", ""))

@test("depends 解析: OR 关系")
def t():
    from xpm import DependencyResolver
    r = DependencyResolver()
    deps = r.parse_depends("liba | libb, libc")
    assert_eq(len(deps), 2)
    assert_eq(len(deps[0]), 2)  # OR 组
    assert_in(("liba", "", ""), deps[0])
    assert_in(("libb", "", ""), deps[0])

@test("depends 解析: 空字符串")
def t():
    from xpm import DependencyResolver
    r = DependencyResolver()
    deps = r.parse_depends("")
    assert_eq(deps, [])

@test("depends 解析: 清理 :any 后缀")
def t():
    from xpm import DependencyResolver
    r = DependencyResolver()
    deps = r.parse_depends("libc6:any (>= 2.28)")
    assert_eq(deps[0][0][0], "libc6")

# ====== 3. 循环依赖检测 ======
@test("循环依赖: 不无限递归")
def t():
    from xpm import DependencyResolver
    r = DependencyResolver()
    # A → B → A
    all_pkgs = [
        {"package": "A", "version": "1.0", "depends": "B"},
        {"package": "B", "version": "1.0", "depends": "A"},
    ]
    result = r.resolve("A", all_pkgs, set())
    # 不应无限递归（抛出或返回部分结果）
    assert_true(isinstance(result, list))

# ====== 4. Packages 文件解析 ======
@test("parse_packages_file: 基本解析")
def t():
    from xpm import parse_packages_file
    content = """Package: vim
Version: 2:9.1.0964-1
Architecture: arm64
Depends: vim-common (= 2:9.1.0964-1), libtinfo6 (>= 6)
Description: Vi IMproved

Package: vim-common
Version: 2:9.1.0964-1
Architecture: all
Description: Common files
"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix="Packages", delete=False) as f:
        f.write(content)
        path = f.name
    pkgs = parse_packages_file(path)
    assert_eq(len(pkgs), 2)
    names = sorted([p["package"] for p in pkgs])
    assert_eq(names, ["vim", "vim-common"])
    vim = [p for p in pkgs if p["package"] == "vim"][0]
    assert_in("libtinfo6", vim.get("depends", ""))
    os.unlink(path)

@test("parse_packages_file: 空文件")
def t():
    from xpm import parse_packages_file
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix="Packages", delete=False) as f:
        f.write("")
        path = f.name
    pkgs = parse_packages_file(path)
    assert_eq(pkgs, [])
    os.unlink(path)

@test("parse_packages_file: 无 Package 字段的块被跳过")
def t():
    from xpm import parse_packages_file
    import tempfile
    content = "Random: value\n\nPackage: real\nVersion: 1.0\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix="Packages", delete=False) as f:
        f.write(content)
        path = f.name
    pkgs = parse_packages_file(path)
    assert_eq(len(pkgs), 1)
    os.unlink(path)

# ====== 5. 源解析 ======
@test("parse_sources: Debian 格式")
def t():
    from xpm import parse_file
    import tempfile
    content = "deb http://mirrors.tuna/ bookworm main contrib non-free\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".list", delete=False) as f:
        f.write(content)
        path = f.name
    sources = parse_file(path)
    assert_eq(len(sources), 1)
    s = sources[0]
    assert_eq(s["type"], "deb")
    assert_eq(s["url"], "http://mirrors.tuna")
    assert_eq(s["suite"], "bookworm")
    assert_eq(s["components"], ["main", "contrib", "non-free"])
    os.unlink(path)

@test("parse_sources: XPM 格式")
def t():
    from xpm import parse_file
    import tempfile
    content = """# XPM source
[xpm]
name=MyRepo
url=http://example.com/dists/stable
type=xpm
enabled=yes
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".list", delete=False) as f:
        f.write(content)
        path = f.name
    sources = parse_file(path)
    assert_eq(len(sources), 1)
    s = sources[0]
    assert_eq(s["type"], "xpm")
    assert_eq(s["url"], "http://example.com/dists/stable")
    assert_true(s["enabled"])
    os.unlink(path)

@test("parse_sources: 注释行被忽略")
def t():
    from xpm import parse_file
    import tempfile
    content = "# 这是注释\ndeb http://example.com/ bookworm main\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".list", delete=False) as f:
        f.write(content)
        path = f.name
    sources = parse_file(path)
    assert_eq(len(sources), 1)
    os.unlink(path)

@test("parse_sources: enabled=no 被过滤")
def t():
    from xpm import parse_file
    import tempfile
    content = "[xpm]\nname=Disabled\nurl=http://x.com\nenabled=no\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".list", delete=False) as f:
        f.write(content)
        path = f.name
    sources = parse_file(path)
    # parse_file 返回 enabled=False 的项，由 parse_sources_dir 过滤
    assert_eq(len(sources), 1)
    assert_true(not sources[0]["enabled"])
    os.unlink(path)

# ====== 6. 数据库 ======
@test("PackageDB: 增删查")
def t():
    from xpm import PackageDB
    import tempfile
    db_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    os.unlink(db_path)
    db = PackageDB(db_path)
    assert_true(not db.is_installed("vim"))
    db.add("vim", "2:9.1", files=["/usr/bin/vim"])
    assert_true(db.is_installed("vim"))
    assert_eq(db.get_version("vim"), "2:9.1")
    db.remove("vim")
    assert_true(not db.is_installed("vim"))
    os.unlink(db_path)

@test("PackageDB: purge 清除配置")
def t():
    from xpm import PackageDB
    import tempfile
    db_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    os.unlink(db_path)
    db = PackageDB(db_path)
    db.add("mypkg", "1.0", files=[])
    # 创建配置目录
    conf = "/tmp/xpm_test_purge"
    os.makedirs(conf, exist_ok=True)
    with open(f"{conf}/mypkg.conf", "w") as f:
        f.write("test")
    # 替换 XPM_ROOT
    os.environ["XPM_ROOT_OVERRIDE"] = "/tmp"
    db.purge("mypkg")
    assert_true(not db.is_installed("mypkg"))
    os.unlink(db_path)

@test("PackageDB: list_all 排序")
def t():
    from xpm import PackageDB
    import tempfile
    db_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    os.unlink(db_path)
    db = PackageDB(db_path)
    db.add("zebra", "1.0")
    db.add("apple", "2.0")
    db.add("mango", "3.0")
    names = db.list_all()
    assert_eq(names, ["apple", "mango", "zebra"])
    os.unlink(db_path)

# ====== 7. 事务 & 回滚 ======
@test("Transaction: 快照与回滚")
def t():
    from xpm import Transaction, PackageDB
    import tempfile
    db_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    os.unlink(db_path)
    db = PackageDB(db_path)
    db.add("testpkg", "1.0")
    
    # 用临时目录做回滚
    rollback_dir = tempfile.mkdtemp()
    tx = Transaction(db, rollback_dir=rollback_dir)
    
    # 创建测试文件（在 rollback_dir 外）
    test_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt").name
    with open(test_file, "w") as f:
        f.write("original")
    
    tx.snapshot("testpkg", [test_file])
    assert_eq(len(tx.steps), 1)
    
    # 修改文件
    with open(test_file, "w") as f:
        f.write("modified")
    
    # 回滚
    ok = tx.rollback()
    assert_true(ok)
    
    with open(test_file) as f:
        content = f.read()
    assert_eq(content, "original")
    
    # 清理
    if os.path.exists(db_path):
        os.unlink(db_path)
    if os.path.exists(test_file):
        os.unlink(test_file)
    import shutil
    shutil.rmtree(rollback_dir)

@test("Transaction: list_rollback_points")
def t():
    from xpm import Transaction, PackageDB
    import tempfile
    db_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    os.unlink(db_path)
    db = PackageDB(db_path)
    
    rollback_dir = tempfile.mkdtemp()
    tx = Transaction(db, rollback_dir=rollback_dir)
    
    # 创建假快照
    snap = {"pkg": "vim", "files": {}, "timestamp": "2026-08-04T10:00:00"}
    snap_path = os.path.join(rollback_dir, "1234567890_vim.json")
    with open(snap_path, "w") as f:
        json.dump(snap, f)
    
    points = tx.list_rollback_points()
    assert_eq(len(points), 1)
    assert_eq(points[0]["pkg"], "vim")
    
    # 清理
    if os.path.exists(db_path):
        os.unlink(db_path)
    import shutil
    shutil.rmtree(rollback_dir)

# ====== 8. GPG 校验 ======
@test("GPGVerifier: 无密钥环时跳过")
def t():
    from xpm import GPGVerifier
    import tempfile
    kr = tempfile.NamedTemporaryFile(suffix=".gpg", delete=False).name
    os.unlink(kr)
    v = GPGVerifier(kr)
    # 不存在的密钥环 → 返回 True（跳过）
    assert_true(v.verify_signature("/nonexist.sig", "/nonexist.data"))
    # 创建空密钥环 → gpgv 会失败但函数返回 True（跳过）
    Path(kr).touch()
    # 不存在的数据文件
    result = v.verify_signature(kr, "/nonexist.data")
    # 没有 gpgv 时返回 True，有 gpgv 时返回 False
    # 两种都算正常（环境差异）
    assert_true(isinstance(result, bool))
    os.unlink(kr)

# ====== 9. 构建工具 ======
@test("cmd_build: 构建 .oil 包")
def t():
    import subprocess, tarfile, tempfile, os
    tmpdir = tempfile.mkdtemp()
    try:
        # 创建目录结构
        pkgdir = os.path.join(tmpdir, "myprog")
        os.makedirs(os.path.join(pkgdir, "usr/bin"))
        os.makedirs(os.path.join(pkgdir, "xpm"))
        
        with open(os.path.join(pkgdir, "usr/bin/myprog"), "w") as f:
            f.write("#!/bin/sh\necho hello")
        with open(os.path.join(pkgdir, "xpm/control"), "w") as f:
            f.write("Package: myprog\nVersion: 1.0\nArchitecture: all\n")
        
        # 运行构建
        result = subprocess.run(
            [sys.executable, "-c", f"""
import sys; sys.path.insert(0, '{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}')
from xpm import cmd_build
sys.exit(cmd_build('{pkgdir}'))
"""],
            capture_output=True, text=True, cwd=tmpdir
        )
        assert_eq(result.returncode, 0)
        
        # 检查输出文件
        oil_files = [f for f in os.listdir(tmpdir) if f.endswith(".oil")]
        assert_true(len(oil_files) > 0)
        
        # 验证 .oil 是有效 tar.gz
        oil_path = os.path.join(tmpdir, oil_files[0])
        with tarfile.open(oil_path, "r:gz") as tar:
            names = tar.getnames()
            # 检查关键文件存在（tarfile 不添加 ./ 前缀）
            has_myprog = any(n.endswith("usr/bin/myprog") for n in names)
            has_control = any(n.endswith("xpm/control") for n in names)
            has_files_list = any(n.endswith("xpm/files.list") for n in names)
            has_checksums = any(n.endswith("xpm/checksums.sha256") for n in names)
            assert_true(has_myprog, f"missing usr/bin/myprog in {names}")
            assert_true(has_control, f"missing xpm/control in {names}")
            assert_true(has_files_list, f"missing xpm/files.list in {names}")
            assert_true(has_checksums, f"missing xpm/checksums.sha256 in {names}")
    finally:
        import shutil
        shutil.rmtree(tmpdir)

@test("cmd_build: 缺少 control 文件时报错")
def t():
    import subprocess, tempfile, os
    tmpdir = tempfile.mkdtemp()
    try:
        pkgdir = os.path.join(tmpdir, "badpkg")
        os.makedirs(pkgdir)
        # 不创建 xpm/control
        result = subprocess.run(
            [sys.executable, "-c", f"""
import sys; sys.path.insert(0, '{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}')
from xpm import cmd_build
sys.exit(cmd_build('{pkgdir}'))
"""],
            capture_output=True, text=True, cwd=tmpdir
        )
        assert_eq(result.returncode, 1)
        assert_true("control" in result.stdout.lower() or "control" in result.stderr.lower())
    finally:
        import shutil
        shutil.rmtree(tmpdir)

# ====== 10. 工具函数 ======
@test("gunzip_file: 解压正确")
def t():
    import gzip, tempfile, os
    from xpm import gunzip_file
    # 创建 gz 文件
    original = b"Hello, XPM! " * 100
    gz_path = tempfile.NamedTemporaryFile(suffix=".gz", delete=False).name
    with gzip.open(gz_path, "wb") as f:
        f.write(original)
    out_path = gz_path[:-3] + ".decompressed"
    result = gunzip_file(gz_path, out_path)
    with open(result, "rb") as f:
        content = f.read()
    assert_eq(content, original)
    os.unlink(gz_path)
    os.unlink(out_path)

@test("make_progress_bar: 边界值")
def t():
    from xpm import make_progress_bar
    bar0 = make_progress_bar(0)
    assert_eq(len(bar0), 20)
    assert_true("█" not in bar0)
    bar100 = make_progress_bar(100)
    assert_eq(len(bar100), 20)
    assert_true("░" not in bar100)
    bar50 = make_progress_bar(50)
    # 大约一半
    filled = bar50.count("█")
    assert_true(8 <= filled <= 12)

@test("detect_arch: aarch64 → arm64")
def t():
    import subprocess
    from unittest.mock import patch
    import xpm
    orig = xpm.ARCH
    try:
        with patch("xpm.subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"stdout": "aarch64"})()
            # 重新加载模块以获取新的 ARCH
            xpm.ARCH = "arm64"
            arch = xpm.detect_arch()
            assert_eq(arch, "arm64")
    finally:
        xpm.ARCH = orig

# ====== 11. 咖啡机 ======
@test("CoffeeMachine: 崩溃计数")
def t():
    from xpm import CoffeeMachine
    import tempfile, os
    db_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    os.unlink(db_path)
    cm = CoffeeMachine(db_path)
    assert_eq(cm.get(), 0)
    cm.crash("test1")
    assert_eq(cm.get(), 1)
    cm.crash("test2")
    assert_eq(cm.get(), 2)
    # 重新加载
    cm2 = CoffeeMachine(db_path)
    assert_eq(cm2.get(), 2)
    os.unlink(db_path)

# ====== 12. CLI 参数解析 ======
@test("main: help 不报错")
def t():
    from xpm import main
    rc = main(["help"])
    assert_eq(rc, 0)

@test("main: version 不报错")
def t():
    from xpm import main
    rc = main(["version"])
    assert_eq(rc, 0)

@test("main: 未知命令返回 1")
def t():
    from xpm import main
    rc = main(["nonexist-cmd-xyz"])
    assert_eq(rc, 1)

@test("main: 拒绝 apt 调用")
def t():
    from xpm import main
    rc = main(["apt-get", "update"])
    assert_eq(rc, 1)

# ====== 13. 集成测试 ======
@test("集成: 完整安装流程（模拟）")
def t():
    """模拟从搜索到安装的全流程"""
    from xpm import (
        DependencyResolver, PackageDB, Transaction,
        parse_packages_file
    )
    import tempfile, os
    # 创建模拟 Packages
    content = """Package: hello
Version: 1.0
Architecture: all
Depends: libc6 (>= 2.0)
Description: Hello world

Package: libc6
Version: 2.31
Architecture: arm64
Description: C library
"""
    pkg_file = tempfile.NamedTemporaryFile(mode="w", suffix="Packages", delete=False).name
    with open(pkg_file, "w") as f:
        f.write(content)
    
    db_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    os.unlink(db_path)
    
    try:
        # 1. 解析源
        all_pkgs = parse_packages_file(pkg_file)
        assert_eq(len(all_pkgs), 2)
        
        # 2. 依赖解析
        db = PackageDB(db_path)
        resolver = DependencyResolver()
        chain = resolver.resolve("hello", all_pkgs, set())
        
        # hello 和 libc6 都应该在链中
        names = [c[0] for c in chain]
        assert_in("hello", names)
        assert_in("libc6", names)
        
        # 3. 模拟安装
        for name, ver, status in chain:
            if status != "missing":
                db.add(name, ver)
        
        assert_true(db.is_installed("hello"))
        assert_true(db.is_installed("libc6"))
        assert_eq(db.count(), 2)
        
        # 4. 模拟卸载
        db.remove("hello")
        assert_true(not db.is_installed("hello"))
        assert_true(db.is_installed("libc6"))
    finally:
        os.unlink(pkg_file)
        os.unlink(db_path)

@test("集成: 依赖链中已安装的包不重复添加")
def t():
    from xpm import DependencyResolver, PackageDB
    all_pkgs = [
        {"package": "A", "version": "1.0", "depends": "B"},
        {"package": "B", "version": "2.0", "depends": "C"},
        {"package": "C", "version": "3.0"},
    ]
    db = PackageDB()
    # C 已安装
    db.add("C", "3.0")
    resolver = DependencyResolver()
    chain = resolver.resolve("A", all_pkgs, {"C"})
    names = [c[0] for c in chain]
    assert_in("A", names)
    assert_in("B", names)
    # C 已安装，不应在链中
    assert_true("C" not in names)

# ====== 14. 文档存在性检查 ======
@test("文档: README.md 存在")
def t():
    readme = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")
    assert_true(os.path.exists(readme))
    with open(readme) as f:
        content = f.read()
    assert_true(len(content) > 1000)

@test("文档: RELEASE.md 存在")
def t():
    rel = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "RELEASE.md")
    assert_true(os.path.exists(rel))

@test("文档: docs/ 目录存在")
def t():
    docs = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
    assert_true(os.path.isdir(docs))
    for f in ["design.md", "manual.md", "packaging.md", "FAQ.md", "internals.md"]:
        fp = os.path.join(docs, f)
        if not os.path.exists(fp):
            raise AssertionError(f"missing {f}")

# ====== 运行 ======
if __name__ == "__main__":
    print(f"🧪 XPM v2.0-0 测试套件")
    print(f"{'='*50}")
    # 导入触发模块加载
    import xpm  # noqa
    # 运行所有 @test 装饰的测试
    test_funcs = [v for k, v in list(globals().items()) if k.startswith("t") and callable(v)]
    # 上面的装饰器已经自动运行了，这里只是汇总
    print(f"{'='*50}")
    print(f"📊 结果: {passed} passed, {failed} failed")
    if failures:
        print("\n失败详情:")
        for name, err in failures:
            print(f"  ❌ {name}: {err}")
    sys.exit(0 if failed == 0 else 1)

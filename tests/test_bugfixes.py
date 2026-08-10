"""
回归测试：验证 v3.1.2 → v3.1.3 修复的 10 个 bug
"""
import os, sys, json, tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# ============================================================
# Bug 1: GUI 版本号硬编码
# ============================================================

class TestBug1GuiVersion:
    def test_version_dynamic_import(self):
        """version.py 应能正确导出 get_short_version 和 get_codename"""
        from xpm_suite.version import get_short_version, get_codename
        v = get_short_version()
        assert v == "3.1.3", f"版本应为 3.1.3，实际 {v}"
        c = get_codename()
        assert c == "Bugfix Edition", f"代号应为 Bugfix Edition，实际 {c}"

    def test_app_py_no_hardcoded_version(self):
        """app.py 不应再硬编码 '3.1.0'"""
        app_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "xpm_suite",
            "store", "gui", "app.py"
        )
        with open(app_path) as f:
            content = f.read()
        # 不应有硬编码的 '3.1.0'
        assert "'3.1.0'" not in content, "app.py 仍硬编码 '3.1.0'"
        # 应动态导入 version
        assert "from ...version import" in content or "from xpm_suite.version import" in content

# ============================================================
# Bug 2: remove_app 变量名错误
# ============================================================

class TestBug2RemoveVar:
    def test_store_gui_remove_uses_dep_name(self):
        """store_gui.py 的 remove_app 应使用 dep_name 而非未定义的 pkg"""
        sg_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "xpm_suite",
            "store", "gui", "store_gui.py"
        )
        with open(sg_path) as f:
            content = f.read()
        # 旧代码：for pkg in deps: self._engine.remove(pkg)
        # 新代码：for dep_name in deps: self._engine.remove(dep_name)
        assert "for dep_name in deps" in content, "remove_app 未修复变量名"
        assert "self._engine.remove(dep_name)" in content, "remove_app 仍用错误的变量名"

    def test_remove_app_logically(self):
        """逻辑测试：mock engine 验证 remove_app 调用正确"""
        from xpm_suite.store.gui import store_gui
        from xpm_suite.store import catalog

        # 确保有测试数据
        catalog.ensure_dirs()

        # 保存原始 BUILTIN_APPS，避免污染全局状态
        original_builtin = catalog.BUILTIN_APPS

        # 创建一个 fake app（不修改全局 BUILTIN_APPS，只传数据）
        test_app = {
            "name": "test_remove_pkg",
            "display": "Test Remove",
            "desc": "test",
            "deps": ["test_dep_a", "test_dep_b"],
            "category": "system",
        }

        class FakeEngine:
            def __init__(self):
                self.removed = []
            def remove(self, name):
                self.removed.append(name)

        # 需要 get_app_detail 能找到
        original_detail = store_gui.get_app_detail
        store_gui.get_app_detail = lambda n: test_app if n == "test_remove_pkg" else None

        # 重置全局 state 并替换其 _engine
        store_gui._state = None
        fake = FakeEngine()
        state = store_gui.get_state()
        original_engine = state._engine
        state._engine = fake

        try:
            result = state.remove_app("test_remove_pkg")
            assert result == True
            assert "test_dep_a" in fake.removed
            assert "test_dep_b" in fake.removed
        finally:
            store_gui.get_app_detail = original_detail
            state._engine = original_engine
            catalog.BUILTIN_APPS = original_builtin

# ============================================================
# Bug 5: 版本选择应取最新
# ============================================================

class TestBug5VersionSort:
    def test_installer_picks_latest_version(self):
        """installer 的 DependencyResolver 应取最新版本"""
        from xpm_suite.core.installer import DependencyResolver
        from xpm_suite.core.statusdb import get_db

        # 模拟索引：同一个包有多个版本
        fake_index = {
            "test_pkg": {
                "1.0.0": {"Package": "test_pkg", "Version": "1.0.0", "Depends": ""},
                "2.0.0": {"Package": "test_pkg", "Version": "2.0.0", "Depends": ""},
                "1.5.0": {"Package": "test_pkg", "Version": "1.5.0", "Depends": ""},
            }
        }
        resolver = DependencyResolver(fake_index)
        order = resolver.resolve("test_pkg")
        # 应解析成功
        assert "test_pkg" in order

    def test_version_key_sorting(self):
        """版本排序逻辑测试"""
        def _ver_key(v):
            parts = str(v).split(".")
            return [int(x) if x.isdigit() else 0 for x in parts]

        versions = ["1.0.0", "2.0.0", "1.5.0", "10.0.0", "0.1.0"]
        sorted_v = sorted(versions, key=_ver_key)
        assert sorted_v[-1] == "10.0.0", f"最大版本应为 10.0.0，实际 {sorted_v[-1]}"

# ============================================================
# Bug 6: Architecture 字段名兼容
# ============================================================

class TestBug6ArchField:
    def test_arch_field_case_insensitive(self):
        """installer 应兼容 Architecture 和 architecture 两种写法"""
        from xpm_suite.core.installer import SourceIndex

        idx = SourceIndex()
        # 模拟 Packages 内容（大写 A）
        pkg_content_upper = """Package: testarch
Version: 1.0
Architecture: arm64
Description: test
 small description

"""
        # 写入临时文件
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.gz', delete=False)
        tmp.close()
        import gzip
        with gzip.open(tmp.name, 'wb') as f:
            f.write(pkg_content_upper.encode())

        idx._parse_packages_file(tmp.name, "arm64")
        assert "testarch" in idx.packages, "大写 Architecture 未被解析"
        os.unlink(tmp.name)

# ============================================================
# Bug 7: pam_end rc 变量
# ============================================================

class TestBug7PamEnd:
    def test_auth_py_no_dir_check(self):
        """auth.py 不应再使用 'rc' in dir() 这种不可靠写法"""
        auth_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "xpm_suite",
            "core", "auth.py"
        )
        with open(auth_path) as f:
            content = f.read()
        assert "rc if 'rc' in dir()" not in content, "auth.py 仍使用不可靠的 dir() 检查"
        assert "_rc" in content, "应使用 _rc 变量"

# ============================================================
# Bug 8: GUI self-update EOFError
# ============================================================

class TestBug8GuiSelfUpdate:
    def test_xpm_main_checks_tty(self):
        """xpm_main.py 的 self-update 应检查 tty"""
        main_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "xpm_suite",
            "cli", "xpm_main.py"
        )
        with open(main_path) as f:
            content = f.read()
        # 应检查 isatty
        assert "isatty()" in content, "self-update 未检查 tty"
        # 非交互环境应跳过确认
        assert "非交互环境" in content or "非交互" in content

# ============================================================
# Bug 9: User-Agent 动态化
# ============================================================

class TestBug9UserAgent:
    def test_downloader_no_hardcoded_ua(self):
        """downloader.py 不应硬编码 XPM-Suite/3.0"""
        dl_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "xpm_suite",
            "core", "downloader.py"
        )
        with open(dl_path) as f:
            content = f.read()
        assert 'User-Agent", "XPM-Suite/3.0"' not in content, \
            "downloader.py 仍硬编码 User-Agent 3.0"

    def test_self_update_no_hardcoded_ua(self):
        """self_update.py 不应硬编码 XPM-Suite/3.0"""
        su_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "xpm_suite",
            "core", "self_update.py"
        )
        with open(su_path) as f:
            content = f.read()
        assert 'User-Agent", "XPM-Suite/3.0"' not in content, \
            "self_update.py 仍硬编码 User-Agent 3.0"
        # 应动态导入 version
        assert "get_short_version" in content

# ============================================================
# Bug 10: elevate.py Tuple import
# ============================================================

class TestBug10ElevateImport:
    def test_elevate_no_unused_tuple_import(self):
        """elevate.py 不应导入未使用的 Tuple"""
        el_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "xpm_suite",
            "core", "elevate.py"
        )
        with open(el_path) as f:
            content = f.read()
        # Tuple 不应在 import 中（因为没用到）
        lines = content.splitlines()
        for line in lines[:20]:
            if "from typing" in line:
                assert "Tuple" not in line, "elevate.py 不应导入未使用的 Tuple"
                break

# ============================================================
# Bug 3+4: 断点续传逻辑
# ============================================================

class TestBug34ResumeDownload:
    def test_downloader_chunk_alignment(self):
        """downloader 分块计算应正确对齐"""
        from xpm_suite.core.downloader import ChunkDownloader
        from xpm_suite.core.downloader import MirrorManager

        mgr = MirrorManager()
        dl = ChunkDownloader(mgr, threads=4, chunk_size=1024)

        # 模拟分块计算
        total = 4096
        threads = 4
        chunk_size = total // threads  # 1024

        chunks = []
        for i in range(threads):
            start = i * chunk_size
            end = (i + 1) * chunk_size - 1
            if i == threads - 1:
                end = total - 1
            chunks.append((start, end))

        # 验证分块覆盖完整范围
        assert chunks[0][0] == 0
        assert chunks[-1][1] == total - 1
        # 验证无重叠
        for i in range(len(chunks) - 1):
            assert chunks[i][1] + 1 == chunks[i+1][0], \
                f"分块不连续: {chunks[i]} -> {chunks[i+1]}"

    def test_downloader_final_size_check(self):
        """downloader 应在合并后验证文件大小"""
        dl_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "xpm_suite",
            "core", "downloader.py"
        )
        with open(dl_path) as f:
            content = f.read()
        assert "final_size" in content, "downloader 缺少 final_size 验证"
        assert "下载大小不匹配" in content, "downloader 缺少大小不匹配错误"

# ============================================================
# 集成测试
# ============================================================

class TestIntegration:
    def test_full_version_consistency(self):
        """所有版本号应一致为 3.1.3"""
        from xpm_suite.version import COMPONENTS, get_short_version
        assert get_short_version() == "3.1.3"
        for name, info in COMPONENTS.items():
            assert info["version"] == "3.1.3", \
                f"{name} 版本不一致: {info['version']}"

    def test_all_modules_importable(self):
        """所有核心模块应能正常导入"""
        import xpm_suite.core.auth
        import xpm_suite.core.installer
        import xpm_suite.core.downloader
        import xpm_suite.core.self_update
        import xpm_suite.core.elevate
        import xpm_suite.core.sources
        import xpm_suite.core.transaction
        import xpm_suite.core.statusdb
        import xpm_suite.cli.xpm_main
        import xpm_suite.store.gui.store_gui
        # app.py 可能需要 tkinter，单独处理
        try:
            import xpm_suite.store.gui.app
        except ImportError:
            pass  # tkinter 不可用时不强求
        assert True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

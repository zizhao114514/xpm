"""
测试 X-Store GUI 模块导入
确保没有越级相对导入 (beyond top-level package)
"""

import sys
import os
import pytest

# 确保 src 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestGuiImports:
    """GUI 模块导入测试 - 防止相对导入越级回归"""

    def test_app_module_importable(self):
        """app.py 必须能直接 import 不报错"""
        import xpm_suite.store.gui.app as app
        assert hasattr(app, "run_gui")
        assert hasattr(app, "XStoreApp")

    def test_store_gui_module_importable(self):
        """store_gui.py 必须能直接 import"""
        import xpm_suite.store.gui.store_gui as sg
        assert hasattr(sg, "StoreState")
        assert hasattr(sg, "get_state")

    def test_theme_module_importable(self):
        """theme.py 必须能直接 import"""
        import xpm_suite.store.gui.theme as theme
        assert hasattr(theme, "get_theme")
        assert hasattr(theme, "THEMES")

    def test_lazy_auth_works(self):
        """_lazy_auth 必须返回可用的 verify_action 和 AuthAction"""
        from xpm_suite.store.gui.app import _lazy_auth
        verify_action, AuthAction = _lazy_auth()
        assert callable(verify_action)
        # AuthAction 是枚举类，检查实际存在的成员
        assert hasattr(AuthAction, "INSTALL")
        assert hasattr(AuthAction, "REMOVE")
        assert hasattr(AuthAction, "UPDATE")

    def test_no_4dot_relative_import(self):
        """确保 app.py 中没有 'from ....' 越级导入"""
        import inspect
        from xpm_suite.store.gui import app
        src = inspect.getsource(app)
        # 不应该有 4 个点的相对导入
        assert "from ...." not in src, (
            "发现越级相对导入 'from ....'，会导致 ImportError: "
            "attempted relative import beyond top-level package"
        )

    def test_no_3dot_relative_in_self_update(self):
        """确保 app.py 中没有 'from ...core' 这种错误层数"""
        import inspect
        from xpm_suite.store.gui import app
        src = inspect.getsource(app)
        # 在 gui/app.py 中：. = gui, .. = store, ... = xpm_suite
        # from ...core 是对的（xpm_suite.core）
        # 但 from ....core 是错的
        lines = src.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("from "):
                assert "...." not in stripped, f"越级导入: {stripped}"

    def test_store_gui_no_4dot_import(self):
        """确保 store_gui.py 中也没有越级导入"""
        import inspect
        from xpm_suite.store.gui import store_gui
        src = inspect.getsource(store_gui)
        assert "from ...." not in src, "store_gui.py 中发现越级导入"

    def test_gui_package_has_init(self):
        """store.gui 包有 __init__.py"""
        import xpm_suite.store.gui as gui_pkg
        init_file = os.path.join(os.path.dirname(gui_pkg.__file__), "__init__.py")
        assert os.path.exists(init_file), "store/gui/__init__.py 不存在"

    def test_run_gui_returns_int_when_no_tk(self, monkeypatch):
        """无 tkinter 时 run_gui 返回 1"""
        # 模拟无 tkinter 环境
        import xpm_suite.store.gui.app as app
        monkeypatch.setattr(app, "HAS_TK", False)
        result = app.run_gui()
        assert result == 1

    def test_self_update_import_from_gui_context(self):
        """从 GUI 上下文中导入 self_update 不报错"""
        # 模拟 gui 模块被加载后导入 self_update
        import xpm_suite.core.self_update as su
        assert hasattr(su, "check_update")
        assert hasattr(su, "perform_update")
        assert hasattr(su, "compare_versions")

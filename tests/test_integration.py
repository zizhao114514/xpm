"""
集成测试: 端到端流程
"""

import sys, os, json, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from unittest import mock

# === xpm CLI 集成 ===

class TestXPMCLI:
    def test_main_help(self, capsys):
        from xpm_suite.cli.xpm_main import main
        rc = main(["--help"])
        out = capsys.readouterr().out
        assert "XPM Suite" in out
        assert rc == 0

    def test_main_version(self, capsys):
        from xpm_suite.cli.xpm_main import main
        rc = main(["version"])
        out = capsys.readouterr().out
        assert "XPM Suite" in out
        assert "3.1" in out

    def test_cmd_arch(self, capsys):
        from xpm_suite.cli.xpm_main import main
        rc = main(["arch"])
        out = capsys.readouterr().out
        assert "架构" in out
        assert rc == 0

    def test_cmd_features(self, capsys):
        from xpm_suite.cli.xpm_main import main
        rc = main(["features"])
        out = capsys.readouterr().out
        assert rc == 0

    def test_cmd_doctor(self, capsys):
        from xpm_suite.cli.xpm_main import main
        rc = main(["doctor"])
        out = capsys.readouterr().out
        assert "诊断" in out or "版本" in out

    def test_cmd_search_no_index(self, capsys):
        from xpm_suite.cli.xpm_main import main
        # 没有索引时应该提示更新
        rc = main(["search", "htop"])
        out = capsys.readouterr().out
        assert rc == 0 or rc == 1

    def test_cmd_list_empty(self, capsys):
        from xpm_suite.cli.xpm_main import main
        rc = main(["list"])
        out = capsys.readouterr().out
        assert rc == 0

    def test_cmd_unknown(self, capsys):
        from xpm_suite.cli.xpm_main import main
        rc = main(["nonexist_cmd_xyz"])
        assert rc != 0

    def test_cmd_install_no_args(self, capsys):
        from xpm_suite.cli.xpm_main import main
        rc = main(["install"])
        out = capsys.readouterr().out
        assert "用法" in out
        assert rc == 1

    def test_cmd_remove_no_args(self, capsys):
        from xpm_suite.cli.xpm_main import main
        rc = main(["remove"])
        out = capsys.readouterr().out
        assert "用法" in out


# === xstore CLI 集成 ===

class TestXStoreCLI:
    def test_main_help(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["--help"])
        out = capsys.readouterr().out
        assert "X-Store" in out
        assert rc == 0

    def test_browse(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["browse"])
        out = capsys.readouterr().out
        assert rc == 0

    def test_list_system(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["list", "system"])
        out = capsys.readouterr().out
        assert "htop" in out.lower() or rc == 0

    def test_top(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["top", "5"])
        out = capsys.readouterr().out
        assert rc == 0

    def test_search(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["search", "git"])
        out = capsys.readouterr().out
        assert "git" in out.lower()

    def test_info_htop(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["info", "htop"])
        out = capsys.readouterr().out
        assert rc == 0

    def test_installed_empty(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["installed"])
        out = capsys.readouterr().out
        assert rc == 0

    def test_rate_valid(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["rate", "htop", "5", "test"])
        assert rc == 0

    def test_rate_invalid(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["rate", "htop", "6"])
        assert rc != 0

    def test_add_custom(self, tmp_path, capsys):
        from xpm_suite.store.cli import main
        import xpm_suite.store.catalog as cat
        cat.CUSTOM_FILE = tmp_path / "custom.json"
        rc = main(["add", "mydev", "git,vim", "开发环境"])
        out = capsys.readouterr().out
        assert "mydev" in out
        assert rc == 0

    def test_remove_custom(self, tmp_path, capsys):
        from xpm_suite.store.cli import main
        import xpm_suite.store.catalog as cat
        cat.CUSTOM_FILE = tmp_path / "custom.json"
        main(["add", "todel", "pkg1"])
        rc = main(["remove-custom", "todel"])
        out = capsys.readouterr().out
        assert "todel" in out

    def test_version(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["version"])
        out = capsys.readouterr().out
        assert "X-Store" in out


# === 完整流程集成 ===

class TestFullFlow:
    def test_install_flow_mock(self, tmp_path):
        """模拟完整的安装流程"""
        from xpm_suite.core.installer import InstallEngine, DependencyResolver
        from xpm_suite.core.statusdb import get_db, PackageStatus
        from xpm_suite.core.transaction import Transaction

        # 构造一个假索引
        fake_index = {
            "mypkg": {
                "1.0-0": {
                    "Package": "mypkg",
                    "Version": "1.0-0",
                    "Architecture": "all",
                    "Depends": "",
                    "Filename": "pool/main/m/mypkg/mypkg_1.0-0_all.deb",
                    "SHA256": "",
                    "Size": "1000",
                    "Description": "Test package",
                }
            }
        }

        resolver = DependencyResolver(fake_index)
        order = resolver.resolve("mypkg")
        assert "mypkg" in order

    def test_deb_to_oil_conversion(self, tmp_path):
        """测试 deb → oil 转换"""
        from xpm_suite.formats.deb import _split_depends
        result = _split_depends("libc6 (>= 2.34) | libmusl, libssl3")
        assert len(result) == 2
        assert "libc6" in result[0][0]

    def test_version_compare_in_scripts(self):
        from xpm_suite.core.scripts_env import _version_compare
        assert _version_compare("1.0-1", "1.0-2") == -1
        assert _version_compare("2.0", "1.5") == 1

    def test_full_feature_chain(self, capsys):
        """测试功能开关链路"""
        from xpm_suite import check, FEATURES
        # 所有功能应该可查询
        for name in FEATURES:
            result = check(name, silent=True)
            assert isinstance(result, bool)

    def test_store_state_full(self):
        """测试 StoreState 完整生命周期"""
        from xpm_suite.store.gui.store_gui import get_state
        s = get_state()
        s.set_category("dev")
        assert s.current_category == "dev"
        s.set_search("vim")
        apps = s.get_visible_apps()
        assert any(a["name"] == "vim" for a in apps)
        s.set_search("")
        s.set_category("system")
        apps = s.get_visible_apps()
        assert len(apps) > 0

    def test_progress_tracker_full(self):
        from xpm_suite.store.gui.store_gui import ProgressTracker
        pt = ProgressTracker()
        pt.update("htop", 50, "500KB/s", "10s")
        data = pt.get("htop")
        assert data["pct"] == 50
        assert data["speed"] == "500KB/s"
        pt.clear("htop")
        assert "htop" not in pt.all()


# === 构建脚本测试 ===

class TestBuildDeb:
    def test_build_script_exists(self):
        build_path = os.path.join(
            os.path.dirname(__file__), "..", "build_deb.py"
        )
        assert os.path.exists(build_path)

    def test_build_script_syntax(self):
        build_path = os.path.join(
            os.path.dirname(__file__), "..", "build_deb.py"
        )
        import py_compile
        py_compile.compile(build_path, doraise=True)

    def test_pyproject_exists(self):
        pyproject = os.path.join(
            os.path.dirname(__file__), "..", "pyproject.toml"
        )
        assert os.path.exists(pyproject)

    def test_desktop_file_exists(self):
        desktop = os.path.join(
            os.path.dirname(__file__), "..", "packaging", "xstore-gui.desktop"
        )
        assert os.path.exists(desktop)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

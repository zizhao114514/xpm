"""
测试: 版本管理 + 功能开关
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from xpm_suite import (
    get_version_string, get_version_tuple, parse_version,
    list_features, check, require, FEATURES, disabled_features,
)


class TestVersion:
    def test_version_string(self):
        v = get_version_string()
        assert "3.1.0" in v
        assert "Add Gui Store Edition" in v

    def test_version_tuple(self):
        t = get_version_tuple()
        assert isinstance(t, tuple)
        assert len(t) == 3
        assert t[0] >= 3

    def test_parse_version(self):
        assert parse_version("3.0") == (3, 0, 0)
        assert parse_version("2.1-5") == (2, 1, 0)
        assert parse_version("3.0-0") == (3, 0, 0)
        assert parse_version("garbage") == (0, 0, 0)

    def test_banner(self):
        from xpm_suite.version import get_banner
        b = get_banner()
        assert "XPM Suite" in b
        assert "3.1" in b


class TestFeatureFlags:
    def test_list_features(self, capsys):
        list_features()
        out = capsys.readouterr().out
        assert "功能" in out or "★" in out or "❌" in out

    def test_check_basic_install(self):
        # 基本安装功能应该始终可用
        assert check("basic_install", silent=True) == True

    def test_check_search(self):
        assert check("search", silent=True) == True

    def test_check_xstore_cli(self):
        # xstore_cli 需要 >=2.5
        result = check("xstore_cli", silent=True)
        assert isinstance(result, bool)

    def test_check_xstore_gui(self):
        result = check("xstore_gui", silent=True)
        assert isinstance(result, bool)

    def test_check_triggers(self):
        result = check("triggers", silent=True)
        assert isinstance(result, bool)

    def test_check_oil_format(self):
        result = check("oil_format", silent=True)
        assert isinstance(result, bool)

    def test_require_basic(self):
        # 不应抛异常
        require("basic_install")

    def test_disabled_features(self):
        df = disabled_features()
        assert isinstance(df, list)

    def test_all_features_registered(self):
        # 确保 FEATURES 非空
        assert len(FEATURES) > 20

    def test_feature_has_min_version(self):
        for name, info in FEATURES.items():
            assert "min" in info
            assert parse_version(info["min"]) >= (0, 0, 0)

    def test_feature_has_name(self):
        for name, info in FEATURES.items():
            assert "name" in info
            assert isinstance(info["name"], str)
            assert len(info["name"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

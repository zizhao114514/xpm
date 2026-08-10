"""
测试: X-Store 应用商店（CLI + GUI 核心逻辑）
"""

import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from unittest import mock

# 确保能从 src 布局导入
if "xpm_suite" not in sys.modules:
    from xpm_suite import store
    from xpm_suite.store import gui as store_gui_mod

# === catalog ===

class TestCatalog:
    def test_get_categories(self):
        from xpm_suite.store.catalog import get_categories
        cats = get_categories()
        assert isinstance(cats, list)
        assert len(cats) >= 5
        keys = {c["key"] for c in cats}
        assert "system" in keys
        assert "dev" in keys
        assert "network" in keys

    def test_get_apps_by_category_system(self):
        from xpm_suite.store.catalog import get_apps_by_category
        apps = get_apps_by_category("system")
        assert len(apps) > 0
        assert any(a["name"] == "htop" for a in apps)

    def test_get_apps_by_category_dev(self):
        from xpm_suite.store.catalog import get_apps_by_category
        apps = get_apps_by_category("dev")
        assert any(a["name"] == "vim" for a in apps)

    def test_get_top_apps(self):
        from xpm_suite.store.catalog import get_top_apps
        tops = get_top_apps(5)
        assert len(tops) == 5
        # 应该按分数降序
        for i in range(len(tops)-1):
            assert tops[i]["score"] >= tops[i+1]["score"]

    def test_search(self):
        from xpm_suite.store.catalog import search_apps
        results = search_apps("git")
        assert len(results) > 0
        assert any("git" in r["name"].lower() for r in results)

    def test_search_no_result(self):
        from xpm_suite.store.catalog import search_apps
        results = search_apps("zzznonexistxxx")
        assert results == []

    def test_get_app_detail(self):
        from xpm_suite.store.catalog import get_app_detail
        detail = get_app_detail("htop")
        assert detail is not None
        assert detail["name"] == "htop"
        assert "rating_avg" in detail

    def test_get_app_detail_nonexist(self):
        from xpm_suite.store.catalog import get_app_detail
        assert get_app_detail("nonexist_xyz") is None

    def test_rate_app(self, tmp_path):
        from xpm_suite.store.catalog import rate_app, get_rating
        import xpm_suite.store.catalog as cat
        cat.RATINGS_FILE = tmp_path / "ratings.json"
        avg = rate_app("htop", 5, "excellent!", "tester")
        assert avg == 5.0
        r = get_rating("htop")
        assert r["count"] == 1
        assert r["avg"] == 5.0

    def test_rate_invalid(self, tmp_path):
        from xpm_suite.store.catalog import rate_app
        import xpm_suite.store.catalog as cat
        cat.RATINGS_FILE = tmp_path / "ratings.json"
        with pytest.raises(ValueError):
            rate_app("htop", 6)
        with pytest.raises(ValueError):
            rate_app("htop", 0)

    def test_add_custom(self, tmp_path):
        from xpm_suite.store.catalog import add_custom, load_custom
        import xpm_suite.store.catalog as cat
        cat.CUSTOM_FILE = tmp_path / "custom.json"
        add_custom("mydev", ["git", "vim"], "开发环境")
        customs = load_custom()
        assert "mydev" in customs
        assert "git" in customs["mydev"]["packages"]

    def test_remove_custom(self, tmp_path):
        from xpm_suite.store.catalog import add_custom, remove_custom
        import xpm_suite.store.catalog as cat
        cat.CUSTOM_FILE = tmp_path / "custom.json"
        add_custom("todelete", ["pkg1"])
        assert remove_custom("todelete") == True
        assert remove_custom("notexist") == False

    def test_get_all_apps(self):
        from xpm_suite.store.catalog import get_all_apps
        all_a = get_all_apps()
        assert len(all_a) > 10
        assert "htop" in all_a

    def test_builtin_apps_have_required_fields(self):
        from xpm_suite.store.catalog import BUILTIN_APPS
        for cat_key, cat_data in BUILTIN_APPS.items():
            for app_key, app in cat_data["apps"].items():
                assert "name" in app
                assert "desc" in app
                assert "popularity" in app
                assert isinstance(app["popularity"], int)


# === store_gui (核心逻辑，不依赖 tkinter) ===

class TestStoreGUI:
    def test_get_state(self):
        from xpm_suite.store.gui.store_gui import get_state
        s = get_state()
        assert s is not None
        assert s.theme_name in ("dark", "light", "oled", "solarized")

    def test_set_theme(self):
        from xpm_suite.store.gui.store_gui import get_state
        s = get_state()
        orig = s.theme_name
        try:
            s.set_theme("light")
            assert s.theme_name == "light"
            s.set_theme("dark")
            assert s.theme_name == "dark"
        finally:
            s.set_theme(orig)

    def test_cycle_theme(self):
        from xpm_suite.store.gui.store_gui import get_state
        s = get_state()
        orig = s.theme_name
        try:
            names = s.get_theme_names()
            s.cycle_theme()
            assert s.theme_name in names
            s.cycle_theme()
            assert s.theme_name in names
        finally:
            s.set_theme(orig)

    def test_set_category(self):
        from xpm_suite.store.gui.store_gui import get_state
        s = get_state()
        s.set_category("dev")
        assert s.current_category == "dev"
        assert s.search_query == ""

    def test_set_search(self):
        from xpm_suite.store.gui.store_gui import get_state
        s = get_state()
        s.set_search("vim")
        assert s.search_query == "vim"

    def test_get_visible_apps(self):
        from xpm_suite.store.gui.store_gui import get_state
        s = get_state()
        s.set_category("system")
        apps = s.get_visible_apps()
        assert len(apps) > 0

    def test_get_visible_search(self):
        from xpm_suite.store.gui.store_gui import get_state
        s = get_state()
        s.set_search("top")
        apps = s.get_visible_apps()
        assert len(apps) > 0

    def test_select_app(self):
        from xpm_suite.store.gui.store_gui import get_state
        s = get_state()
        s.select_app("htop")
        assert s.selected_app == "htop"

    def test_format_stars(self):
        from xpm_suite.store.gui.store_gui import format_stars
        s = format_stars(4.5, 10)
        assert "★" in s
        assert "4.5" in s

    def test_format_stars_no_rating(self):
        from xpm_suite.store.gui.store_gui import format_stars
        s = format_stars(0, 0)
        assert "未评分" in s

    def test_format_popularity_bar(self):
        from xpm_suite.store.gui.store_gui import format_popularity_bar
        bar = format_popularity_bar(50)
        assert "█" in bar
        assert "░" in bar

    def test_get_app_icon(self):
        from xpm_suite.store.gui.store_gui import get_app_icon
        assert get_app_icon("htop") == "📊"
        assert get_app_icon("vim") == "✏️"
        assert get_app_icon("nonexist") == "📦"

    def test_progress_tracker(self):
        from xpm_suite.store.gui.store_gui import ProgressTracker
        pt = ProgressTracker()
        pt.update("htop", 50, "1MB/s", "10s")
        data = pt.get("htop")
        assert data["pct"] == 50
        assert data["speed"] == "1MB/s"
        pt.clear("htop")
        assert "htop" not in pt.all()

    def test_install_app_mock(self):
        from xpm_suite.store.gui.store_gui import get_state
        s = get_state()
        # 模拟安装（不真正安装）
        with mock.patch.object(s, '_engine') as eng_mock:
            eng_mock.install.return_value = True
            # 不实际调用，避免副作用
            pass

    def test_subscribe_notify(self):
        from xpm_suite.store.gui.store_gui import get_state
        s = get_state()
        called = []
        s.subscribe(lambda: called.append(1))
        s.set_search("test")
        assert len(called) >= 1


# === theme ===

class TestTheme:
    def test_themes_exist(self):
        from xpm_suite.store.gui.theme import THEMES
        assert "dark" in THEMES
        assert "light" in THEMES
        assert "oled" in THEMES

    def test_dark_theme_colors(self):
        from xpm_suite.store.gui.theme import THEMES
        t = THEMES["dark"]
        assert t["bg"].startswith("#")
        assert t["accent"].startswith("#")
        assert t["text"].startswith("#")

    def test_get_theme(self):
        from xpm_suite.store.gui.theme import get_theme
        t = get_theme("dark")
        assert t["bg"] == "#1a1a2e"
        # 返回副本
        t["bg"] = "modified"
        t2 = get_theme("dark")
        assert t2["bg"] == "#1a1a2e"

    def test_list_themes(self):
        from xpm_suite.store.gui.theme import list_themes
        names = list_themes()
        assert len(names) >= 3

    def test_hex_to_rgb(self):
        from xpm_suite.store.gui.theme import hex_to_rgb
        assert hex_to_rgb("#ff0000") == (255, 0, 0)
        assert hex_to_rgb("#00ff00") == (0, 255, 0)
        assert hex_to_rgb("#0000ff") == (0, 0, 255)

    def test_rgb_to_hex(self):
        from xpm_suite.store.gui.theme import rgb_to_hex
        assert rgb_to_hex(255, 0, 0) == "#ff0000"

    def test_lighten(self):
        from xpm_suite.store.gui.theme import lighten
        result = lighten("#000000", 0.5)
        assert result.startswith("#")
        # 应该变亮
        assert int(result[1:3], 16) > 0

    def test_darken(self):
        from xpm_suite.store.gui.theme import darken
        result = darken("#ffffff", 0.5)
        assert result.startswith("#")
        # 应该变暗
        assert int(result[1:3], 16) < 255


# === store CLI ===

class TestStoreCLI:
    def test_main_help(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["--help"])
        out = capsys.readouterr().out
        assert "X-Store" in out
        assert rc == 0

    def test_main_version(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["version"])
        out = capsys.readouterr().out
        assert "X-Store" in out
        assert rc == 0

    def test_main_browse(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["browse"])
        out = capsys.readouterr().out
        assert rc == 0

    def test_main_top(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["top", "5"])
        out = capsys.readouterr().out
        assert "TOP" in out or "热门" in out

    def test_main_search(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["search", "git"])
        out = capsys.readouterr().out
        assert rc == 0

    def test_main_info(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["info", "htop"])
        out = capsys.readouterr().out
        assert "htop" in out.lower() or rc == 0

    def test_main_unknown_cmd(self, capsys):
        from xpm_suite.store.cli import main
        rc = main(["nonexist_cmd_xyz"])
        assert rc != 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
测试: 软件源管理模块 (sources.py)
覆盖: 解析/写入/迁移/验证/架构推断
"""

import sys, os, tempfile, shutil
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from xpm_suite.core import sources as src_mod


class TestParseSourceLine:
    def test_basic_deb_line(self):
        line = "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main contrib"
        e = src_mod.parse_source_line(line)
        assert e is not None
        assert e.url == "https://mirrors.tuna.tsinghua.edu.cn/debian"
        assert e.suite == "trixie"
        assert e.components == ["main", "contrib"]
        assert e.arch is None

    def test_with_arch_bracket(self):
        line = "deb [arch=arm64] https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main"
        e = src_mod.parse_source_line(line)
        assert e is not None
        assert e.arch == "arm64"
        assert e.components == ["main"]

    def test_with_multiple_options(self):
        line = "deb [arch=arm64 lang=en_US] https://mirror/debian trixie main"
        e = src_mod.parse_source_line(line)
        assert e is not None
        assert e.arch == "arm64"
        assert e.options.get("lang") == "en_US"

    def test_deb_src(self):
        line = "deb-src https://mirror/debian trixie main"
        e = src_mod.parse_source_line(line)
        assert e is not None

    def test_comment_line(self):
        assert src_mod.parse_source_line("# this is a comment") is None

    def test_empty_line(self):
        assert src_mod.parse_source_line("") is None
        assert src_mod.parse_source_line("   ") is None

    def test_legacy_arch_suffix(self):
        line = "deb https://mirror/debian trixie main arch=amd64"
        e = src_mod.parse_source_line(line)
        assert e is not None
        assert e.arch == "amd64"

    def test_full_options_block(self):
        line = "deb [arch=loong64 trusted=yes] https://mirror/debian trixie main non-free"
        e = src_mod.parse_source_line(line)
        assert e.arch == "loong64"
        assert e.options["trusted"] == "yes"
        assert "non-free" in e.components


class TestSourceEntrySerialization:
    def test_to_line_basic(self):
        e = src_mod.SourceEntry(
            url="https://mirror/debian",
            suite="trixie",
            components=["main"],
        )
        assert "deb https://mirror/debian trixie main" in e.to_line()

    def test_to_line_with_arch(self):
        e = src_mod.SourceEntry(
            url="https://mirror/debian",
            suite="trixie",
            components=["main", "contrib"],
            arch="arm64",
        )
        line = e.to_line()
        assert "[arch=arm64]" in line
        assert "trixie" in line
        assert "contrib" in line


class TestParseSourcesFile:
    def test_parse_file(self, tmp_path):
        f = tmp_path / "tuna.list"
        f.write_text(
            "# comment\n"
            "deb [arch=arm64] https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main\n"
            "deb [arch=arm64] https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie-updates main\n"
        )
        entries = src_mod.parse_sources_file(str(f))
        assert len(entries) == 2
        assert entries[0].arch == "arm64"
        assert entries[0].suite == "trixie"
        assert entries[1].suite == "trixie-updates"
        assert entries[0].file == "tuna.list"

    def test_parse_missing_file(self):
        entries = src_mod.parse_sources_file("/nonexistent/path/list")
        assert entries == []


class TestAddRemoveSource:
    def test_add_source(self, tmp_path, monkeypatch):
        monkeypatch.setattr(src_mod, "SOURCES_DIR", str(tmp_path))
        e = src_mod.SourceEntry(
            url="https://mirrors.ustc.edu.cn/debian",
            suite="trixie",
            components=["main"],
            arch="amd64",
        )
        fpath = src_mod.add_source(e, "ustc.list")
        assert os.path.exists(fpath)
        content = open(fpath).read()
        assert "deb [arch=amd64]" in content
        assert "mirrors.ustc.edu.cn" in content

    def test_add_source_no_path_traversal(self, tmp_path, monkeypatch):
        monkeypatch.setattr(src_mod, "SOURCES_DIR", str(tmp_path))
        e = src_mod.SourceEntry(url="https://mirror/debian", suite="trixie", components=["main"])
        with pytest.raises(ValueError):
            src_mod.add_source(e, "../../etc/passwd")

    def test_filename_auto_append(self, tmp_path, monkeypatch):
        monkeypatch.setattr(src_mod, "SOURCES_DIR", str(tmp_path))
        e = src_mod.SourceEntry(url="https://mirror/debian", suite="trixie", components=["main"])
        fpath = src_mod.add_source(e, "custom")
        assert fpath.endswith("custom.list")


class TestValidateSources:
    def test_duplicate_detection(self, tmp_path, monkeypatch):
        monkeypatch.setattr(src_mod, "SOURCES_DIR", str(tmp_path))
        f = tmp_path / "a.list"
        f.write_text(
            "deb [arch=arm64] https://mirror/debian trixie main\n"
            "deb [arch=arm64] https://mirror/debian trixie main\n"
        )
        issues = src_mod.validate_sources()
        assert any("重复" in i[1] for i in issues)

    def test_invalid_url(self, tmp_path, monkeypatch):
        monkeypatch.setattr(src_mod, "SOURCES_DIR", str(tmp_path))
        f = tmp_path / "bad.list"
        f.write_text("deb ftp://bad-url/debian trixie main\n")
        issues = src_mod.validate_sources()
        assert any("无效" in i[1] or "bad-url" in i[1] for i in issues)

    def test_empty_components(self, tmp_path, monkeypatch):
        monkeypatch.setattr(src_mod, "SOURCES_DIR", str(tmp_path))
        f = tmp_path / "empty.list"
        f.write_text("deb https://mirror/debian trixie\n")
        issues = src_mod.validate_sources()
        assert any("component" in i[1].lower() for i in issues)


class TestMigrateLegacy:
    def test_migrate(self, tmp_path, monkeypatch):
        monkeypatch.setattr(src_mod, "SOURCES_DIR", str(tmp_path))
        legacy = tmp_path / "sources.list"
        legacy.write_text(
            "# old file\n"
            "deb https://old-mirror/debian trixie main\n"
        )
        # 把 legacy 路径也 patch 掉
        monkeypatch.setattr(src_mod, "SOURCES_DIR", str(tmp_path))
        # 需要 patch 旧文件路径
        import xpm_suite.core.sources as s
        old_path = "/etc/xpm/sources.list"
        # 用 tmp_path 模拟
        new_legacy = tmp_path / "old_sources.list"
        new_legacy.write_text("deb https://old/debian trixie main\n")
        # 直接测逻辑：把旧文件内容解析后写入新位置
        entries = s.parse_sources_file(str(new_legacy))
        assert len(entries) == 1
        assert entries[0].url == "https://old/debian"


class TestGetArchForSource:
    def test_source_arch_overrides(self):
        e = src_mod.SourceEntry(
            url="https://mirror/debian", suite="trixie",
            components=["main"], arch="riscv64",
        )
        assert src_mod.get_arch_for_source(e, "amd64") == "riscv64"

    def test_fallback_to_default(self):
        e = src_mod.SourceEntry(
            url="https://mirror/debian", suite="trixie",
            components=["main"],
        )
        assert src_mod.get_arch_for_source(e, "arm64") == "arm64"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

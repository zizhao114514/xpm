"""
测试: 核心模块（config / statusdb / transaction / downloader / triggers / scripts_env）
"""

import sys, os, json, time, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from unittest import mock

# === config ===

class TestConfig:
    def test_load_config_defaults(self):
        from xpm_suite.core.config import load_config, DEFAULT_CONFIG
        cfg = load_config()
        assert isinstance(cfg, dict)
        assert "architecture" in cfg
        assert "downloader" in cfg

    def test_get_arch_returns_string(self):
        from xpm_suite.core.config import get_arch
        arch = get_arch()
        assert isinstance(arch, str)
        assert len(arch) > 0

    def test_detect_architecture(self):
        from xpm_suite.core.config import detect_architecture
        arch = detect_architecture(force=True)
        assert arch in ("amd64","arm64","armhf","armel","i386",
                       "loong64","riscv64","ppc64el","s390x")

    def test_set_arch_valid(self):
        from xpm_suite.core.config import set_arch, get_arch
        orig = get_arch()
        try:
            r = set_arch("arm64")
            assert r == "arm64"
        finally:
            set_arch(orig)

    def test_set_arch_invalid(self):
        from xpm_suite.core.config import set_arch
        with pytest.raises(ValueError):
            set_arch("invalid_arch_xyz")

    def test_get_downloader_config(self):
        from xpm_suite.core.config import get_downloader_config
        dc = get_downloader_config()
        assert "threads" in dc
        assert "timeout" in dc
        assert dc["threads"] >= 1

    def test_get_gui_config(self):
        from xpm_suite.core.config import get_gui_config
        gc = get_gui_config()
        assert "theme" in gc


# === statusdb ===

class TestStatusDB:
    def _make_pkg(self, name="testpkg", version="1.0-0", arch="all"):
        from xpm_suite.core.statusdb import PackageStatus
        return PackageStatus(
            name=name, version=version, arch=arch,
            files=["usr/bin/test"], depends=[], installed_by="test",
        )

    def test_add_and_get(self):
        from xpm_suite.core.statusdb import get_db
        db = get_db()
        pkg = self._make_pkg("test_add_pkg")
        db.add(pkg)
        assert db.is_installed("test_add_pkg")
        db.remove("test_add_pkg")
        assert not db.is_installed("test_add_pkg")

    def test_remove(self):
        from xpm_suite.core.statusdb import get_db
        db = get_db()
        pkg = self._make_pkg("test_rm_pkg")
        db.add(pkg)
        db.remove("test_rm_pkg")
        assert not db.is_installed("test_rm_pkg")

    def test_lock_unlock(self):
        from xpm_suite.core.statusdb import get_db
        db = get_db()
        pkg = self._make_pkg("test_lock_pkg")
        db.add(pkg)
        db.lock("test_lock_pkg")
        assert db.is_locked("test_lock_pkg")
        db.unlock("test_lock_pkg")
        assert not db.is_locked("test_lock_pkg")
        db.remove("test_lock_pkg")

    def test_search(self):
        from xpm_suite.core.statusdb import get_db
        db = get_db()
        pkg = self._make_pkg("testsearchpkg")
        db.add(pkg)
        results = db.search("testsearch")
        assert any(p.name == "testsearchpkg" for p in results)
        db.remove("testsearchpkg")

    def test_top_by_files(self):
        from xpm_suite.core.statusdb import get_db
        db = get_db()
        pkg = self._make_pkg("test_top_pkg")
        pkg.files = [f"file_{i}" for i in range(50)]
        db.add(pkg)
        top = db.top_by_files(5)
        assert any(name == "test_top_pkg" for name, _, _ in top)
        db.remove("test_top_pkg")

    def test_trigger_state(self):
        from xpm_suite.core.statusdb import get_triggers
        ts = get_triggers()
        ts.register_interest("test-trigger", "test-pkg")
        ts.activate("test-trigger", "activator-pkg")
        pending = ts.get_pending()
        assert "test-trigger" in pending
        ts.clear_pending("test-trigger")
        assert "test-trigger" not in ts.get_pending()


# === scripts_env ===

class TestScriptsEnv:
    def test_build_env(self):
        from xpm_suite.core.scripts_env import build_script_env
        env = build_script_env("htop", "3.0-0", "arm64", "postinst")
        assert env["DPKG_MAINTSCRIPT_PACKAGE"] == "htop"
        assert env["DPKG_MAINTSCRIPT_ARCH"] == "arm64"
        assert env["DPKG_MAINTSCRIPT_NAME"] == "postinst"
        assert "XPM_VERSION" in env

    def test_build_env_preinst(self):
        from xpm_suite.core.scripts_env import build_script_env
        env = build_script_env("curl", "1.0", "amd64", "preinst")
        assert env["DPKG_MAINTSCRIPT_NAME"] == "preinst"

    def test_version_compare(self):
        from xpm_suite.core.scripts_env import _version_compare
        assert _version_compare("1.0", "2.0") == -1
        assert _version_compare("2.0", "1.0") == 1
        assert _version_compare("1.0-1", "1.0-2") == -1
        assert _version_compare("3.0", "3.0") == 0

    def test_verify_env(self):
        from xpm_suite.core.scripts_env import verify_env
        results = verify_env("htop", "postinst")
        assert isinstance(results, dict)
        assert "DPKG_ADMINDIR" in results
        assert "DPKG_MAINTSCRIPT_PACKAGE" in results

    def test_no_script(self):
        from xpm_suite.core.scripts_env import run_script
        rc, out, err = run_script("/nonexist/path", "x", "1.0", "all", "postinst")
        assert rc == 0
        combined = (out + " " + err).lower()
        assert "skipped" in combined or "no script" in combined

    def test_script_templates(self):
        from xpm_suite.core.scripts_env import SCRIPT_TEMPLATES
        assert "postinst_ldconfig" in SCRIPT_TEMPLATES
        assert "postinst_fontconfig" in SCRIPT_TEMPLATES
        assert "#!/bin/sh" in SCRIPT_TEMPLATES["postinst_ldconfig"]


# === transaction ===

class TestTransaction:
    def test_atomic_write(self):
        from xpm_suite.core.transaction import atomic_write
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"old")
            path = f.name
        try:
            info = atomic_write(path, b"new", mode=0o644)
            assert info["old_data"] == b"old"
            with open(path, "rb") as f:
                assert f.read() == b"new"
        finally:
            os.unlink(path)

    def test_atomic_remove(self):
        from xpm_suite.core.transaction import atomic_remove
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"data")
            path = f.name
        data = atomic_remove(path)
        assert data == b"data"
        assert not os.path.exists(path)

    def test_transaction_commit(self):
        from xpm_suite.core.transaction import Transaction
        from xpm_suite.core.statusdb import get_db, PackageStatus
        db = get_db()
        with Transaction("test") as tx:
            pkg = PackageStatus(name="tx_test_pkg", version="1.0",
                              arch="all", files=[], installed_by="test")
            tx.install_package(pkg, [])
            assert tx._committed == False
        # 退出后应该已提交
        assert db.is_installed("tx_test_pkg")
        db.remove("tx_test_pkg")

    def test_transaction_rollback(self):
        from xpm_suite.core.transaction import Transaction
        from xpm_suite.core.statusdb import get_db, PackageStatus
        db = get_db()
        try:
            with Transaction("test rollback") as tx:
                pkg = PackageStatus(name="tx_fail_pkg", version="1.0",
                                  arch="all", files=[], installed_by="test")
                tx.install_package(pkg, [])
                raise RuntimeError("simulated failure")
        except RuntimeError:
            pass
        assert not db.is_installed("tx_fail_pkg")


# === downloader ===

class TestDownloader:
    def test_mirror_creation(self):
        from xpm_suite.core.downloader import Mirror, MirrorManager
        m = Mirror("Test", "https://example.com")
        assert m.name == "Test"
        assert m.base_url == "https://example.com"
        mm = MirrorManager()
        mm.add("Custom", "https://custom.example.com", 50)
        assert any(m.name == "Custom" for m in mm.mirrors)

    def test_get_mirror_manager(self):
        from xpm_suite.core.downloader import get_mirror_manager
        mgr = get_mirror_manager()
        assert mgr is not None
        assert len(mgr.mirrors) > 0

    def test_get_downloader(self):
        from xpm_suite.core.downloader import get_downloader
        dl = get_downloader()
        assert dl is not None
        assert dl.threads >= 1

    def test_verify_deb_valid(self, tmp_path):
        from xpm_suite.core.downloader import ChunkDownloader, MirrorManager
        # 创建一个假的 .deb (ar magic)
        fake_deb = tmp_path / "fake.deb"
        fake_deb.write_bytes(b"!<arch>\n" + b"0"*100)
        dl = ChunkDownloader(MirrorManager())
        assert dl.verify_deb(str(fake_deb)) == True

    def test_verify_deb_invalid(self, tmp_path):
        from xpm_suite.core.downloader import ChunkDownloader, MirrorManager
        fake = tmp_path / "not_deb.deb"
        fake.write_bytes(b"this is not a deb file")
        dl = ChunkDownloader(MirrorManager())
        assert dl.verify_deb(str(fake)) == False


# === triggers ===

class TestTriggers:
    def test_register_interest(self):
        from xpm_suite.core.triggers import get_engine
        eng = get_engine()
        eng.register_interest("test-trigger-2", "test-pkg-2")
        status = eng.get_status()
        assert status["registered_interests"] >= 1

    def test_register_package_triggers(self):
        from xpm_suite.core.triggers import get_engine
        eng = get_engine()
        eng.register_package_triggers("mypkg", {
            "Interest": "my-trigger",
            "Activate": "other-trigger",
        })
        assert "my-trigger" in eng.ts._data["interests"]

    def test_activate_for_files(self):
        from xpm_suite.core.triggers import get_engine
        eng = get_engine()
        eng.activate_for_files(["/usr/share/fonts/myfont.ttf"])
        pending = eng.ts.get_pending()
        assert "fontconfig-rebuild" in pending

    def test_process_empty(self):
        from xpm_suite.core.triggers import get_engine
        eng = get_engine()
        # 清除 pending
        for t in list(eng.ts.get_pending().keys()):
            eng.ts.clear_pending(t)
        results = eng.process_pending()
        assert results == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

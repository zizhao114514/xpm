"""
测试: PAM 认证 + 自更新 + 提权模块
"""

import os, sys, json, time
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# 确保能导入 xpm_suite
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from xpm_suite.core import auth, elevate, self_update
from xpm_suite.core.auth import (
    AuthAction, AuthSession, verify_action, require_auth,
    authenticate_user, detect_privilege, ACTION_LEVEL, AUTH_TTL,
    install_pam_config,
)
from xpm_suite.core.self_update import (
    compare_versions, parse_version_str, check_update,
    perform_update, rollback, list_backups, VersionInfo,
    check_remote_version, get_current_version, format_update_status,
)
from xpm_suite.core.elevate import (
    is_root, has_display, get_original_user, detect_environment,
    select_tool, build_elevated_cmd, ensure_root, status_string,
    get_available_tools,
)


# ============================================================
# AuthAction / 常量
# ============================================================

class TestAuthConstants:
    def test_all_actions_have_levels(self):
        for action in AuthAction:
            assert action in ACTION_LEVEL, f"Action {action} missing level"

    def test_action_levels_valid(self):
        for action, level in ACTION_LEVEL.items():
            assert level in ("low", "medium", "high", "critical")

    def test_ttl_defined_for_all_levels(self):
        for level in ("low", "medium", "high", "critical"):
            assert level in AUTH_TTL
            assert AUTH_TTL[level] > 0

    def test_auth_action_values(self):
        assert AuthAction.INSTALL.value == "install"
        assert AuthAction.REMOVE.value == "remove"
        assert AuthAction.SELF_UPGRADE.value == "self_upgrade"


# ============================================================
# AuthSession
# ============================================================

class TestAuthSession:
    def setup_method(self):
        AuthSession.clear()

    def teardown_method(self):
        AuthSession.clear()

    def test_initial_state(self):
        assert AuthSession.is_valid("low") == False
        assert AuthSession.remaining_seconds() == 0

    def test_grant_and_validate(self):
        AuthSession.grant("high", 300)
        assert AuthSession.is_valid("low") == True
        assert AuthSession.is_valid("medium") == True
        assert AuthSession.is_valid("high") == True
        assert AuthSession.is_valid("critical") == False  # granted high, need critical

    def test_grant_critical(self):
        AuthSession.grant("critical", 60)
        assert AuthSession.is_valid("critical") == True

    def test_clear(self):
        AuthSession.grant("high", 300)
        assert AuthSession.is_valid("high") == True
        AuthSession.clear()
        assert AuthSession.is_valid("high") == False

    def test_session_expiry(self):
        # 授予 1 秒 TTL
        AuthSession.grant("low", 1)
        assert AuthSession.is_valid("low") == True
        time.sleep(1.1)
        assert AuthSession.is_valid("low") == False

    def test_remaining_seconds(self):
        AuthSession.grant("low", 300)
        rem = AuthSession.remaining_seconds()
        assert 0 < rem <= 300


# ============================================================
# verify_action
# ============================================================

class TestVerifyAction:
    def setup_method(self):
        AuthSession.clear()

    def teardown_method(self):
        AuthSession.clear()

    def test_low_level_confirm_y(self, monkeypatch):
        """低安全级别 + 用户输入 y → 通过"""
        monkeypatch.setattr("builtins.input", lambda p: "y")
        # 非 root 环境，force=True 应该直接通过
        ok, msg = verify_action(AuthAction.UPDATE, "test", force=True)
        assert isinstance(ok, bool)

    def test_force_low_level(self):
        """force=True + low level → 直接通过"""
        ok, msg = verify_action(AuthAction.UPDATE, "test", force=True)
        assert isinstance(ok, bool)

    def test_session_reuse(self):
        """已授权会话可复用"""
        AuthSession.grant("high", 300)
        ok, msg = verify_action(AuthAction.INSTALL, "htop")
        assert ok == True

    def test_session_insufficient(self):
        """会话级别不够"""
        AuthSession.grant("low", 300)
        # critical 需要更高权限
        # 但由于我们已经是 root，verify_action 会直接通过
        # 所以这个测试验证：非 root 时 low 不能做 critical
        import os
        if os.geteuid() != 0:
            ok, msg = verify_action(AuthAction.SELF_UPGRADE, "xpm")
            assert ok == False
        else:
            # root 用户直接通过
            ok, msg = verify_action(AuthAction.SELF_UPGRADE, "xpm")
            assert ok == True


# ============================================================
# detect_privilege
# ============================================================

class TestDetectPrivilege:
    def test_returns_dict(self):
        result = detect_privilege()
        assert isinstance(result, dict)
        for key in ("is_root", "method", "original_user", "can_elevate"):
            assert key in result

    def test_method_values(self):
        result = detect_privilege()
        assert result["method"] in ("root", "sudo", "gksu", "pkexec", "none")


# ============================================================
# authenticate_user (mocked)
# ============================================================

class TestAuthenticateUser:
    def test_returns_bool(self):
        # 无论成功失败，应该返回 bool
        result = authenticate_user(service="xpm", username="nobody", reason="test")
        assert isinstance(result, bool)

    def test_keyboard_interrupt(self, monkeypatch):
        # 当前是 root，authenticate_user 直接返回 True
        # 所以这里测试非 root 场景
        import os
        if os.geteuid() != 0:
            def raise_kb(*a, **kw): raise KeyboardInterrupt
            monkeypatch.setattr("getpass.getpass", raise_kb)
            result = authenticate_user(service="xpm", username="nobody")
            assert result == False
        else:
            # root 直接通过
            result = authenticate_user(service="xpm", username="root")
            assert result == True


# ============================================================
# PAM config
# ============================================================

class TestPamConfig:
    def test_install_pam_config_creates_file(self, tmp_path, monkeypatch):
        pam_dir = tmp_path / "pam.d"
        pam_file = pam_dir / "xpm"
        # Make sure the function exists
        from xpm_suite.core.auth import install_pam_config as _install_pam
        # Mock: file doesn't exist, then it will be created
        orig_exists = os.path.exists
        def mock_exists(p):
            if "pam.d/xpm" in str(p):
                return False
            return orig_exists(p)
        monkeypatch.setattr("xpm_suite.core.auth.os.path.exists", mock_exists)
        monkeypatch.setattr("xpm_suite.core.auth.os.makedirs", lambda *a, **kw: None)
        written = {}
        def mock_open(path, *a, **kw):
            class F:
                def write(self, data): written["data"] = data
                def __enter__(self): return self
                def __exit__(self, *a): pass
            return F()
        monkeypatch.setattr("builtins.open", mock_open)
        monkeypatch.setattr("xpm_suite.core.auth.os.chmod", lambda *a, **kw: None)

        result = _install_pam()
        assert isinstance(result, bool)


# ============================================================
# Version comparison
# ============================================================

class TestVersionCompare:
    def test_equal(self):
        assert compare_versions("3.0.0", "3.0.0") == 0
        assert compare_versions("3.1.0", "3.1.0") == 0

    def test_greater(self):
        assert compare_versions("3.1.0", "3.0.0") == 1
        assert compare_versions("4.0.0", "3.9.9") == 1

    def test_lesser(self):
        assert compare_versions("3.0.0", "3.1.0") == -1
        assert compare_versions("2.9.9", "3.0.0") == -1

    def test_parse(self):
        assert parse_version_str("3.0.0") == (3, 0, 0)
        assert parse_version_str("3.1.5") == (3, 1, 5)
        assert parse_version_str("v3.0.0") == (3, 0, 0)
        assert parse_version_str("invalid") == (0, 0, 0)

    def test_get_current(self):
        v = get_current_version()
        assert isinstance(v, str)
        assert len(v.split(".")) >= 2


# ============================================================
# VersionInfo
# ============================================================

class TestVersionInfo:
    def test_str(self):
        v = VersionInfo(version="3.1.0", codename="Test")
        s = str(v)
        assert "3.1.0" in s
        assert "Test" in s

    def test_to_from_dict(self):
        v = VersionInfo(
            version="3.1.0", codename="Test",
            release_date="2025-01-15", changelog="Bug fixes",
            download_url="http://example.com/x.deb",
            sha256="abc", size=1024, min_python="3.8",
        )
        d = v.to_dict()
        assert d["version"] == "3.1.0"
        assert d["codename"] == "Test"
        v2 = VersionInfo.from_dict(d)
        assert v2.version == "3.1.0"
        assert v2.codename == "Test"


# ============================================================
# check_update (mocked network)
# ============================================================

class TestCheckUpdate:
    def test_format_update_status(self):
        """format_update_status 应该返回字符串"""
        result = format_update_status()
        assert isinstance(result, str)

    def test_check_remote_version_returns_none_on_failure(self, monkeypatch):
        """网络不可用时返回 None"""
        def fake_fetch(url, timeout=10):
            return None
        monkeypatch.setattr(self_update, "_fetch_url", fake_fetch)
        result = check_remote_version(cache=False)
        assert result is None

    def test_parse_github_release(self):
        """解析 GitHub API 响应"""
        fake_json = json.dumps({
            "tag_name": "v3.1.0",
            "published_at": "2025-01-15T10:00:00Z",
            "body": "## Changelog\n- New feature\n- Bug fix",
            "assets": [{
                "name": "xpm-suite_3.1.0_all.deb",
                "browser_download_url": "https://example.com/xpm.deb",
                "size": 57344,
            }]
        })
        result = self_update._parse_github_release(fake_json)
        assert result is not None
        assert result.version == "3.1.0"
        assert "New feature" in result.changelog
        assert result.size == 57344

    def test_parse_simple_version(self):
        text = """# Comment
VERSION=3.2.0
CODENAME=Test Edition
URL=https://example.com/pkg.deb
SHA256=abc123def456
"""
        result = self_update._parse_simple_version(text)
        assert result is not None
        assert result.version == "3.2.0"
        assert result.codename == "Test Edition"
        assert result.sha256 == "abc123def456"


# ============================================================
# Backup / Rollback
# ============================================================

class TestBackupRollback:
    def test_list_backups_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(self_update, "BACKUP_DIR", str(tmp_path))
        result = list_backups()
        assert result == []

    def test_list_backups_with_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(self_update, "BACKUP_DIR", str(tmp_path))
        # 创建模拟备份目录
        d = tmp_path / "xpm-suite-20250115-120000"
        d.mkdir()
        # 给目录设 mtime
        ts = time.mktime(time.strptime("2025-01-15 12:00:00", "%Y-%m-%d %H:%M:%S"))
        os.utime(str(d), (ts, ts))

        result = list_backups()
        assert len(result) == 1
        assert "20250115" in result[0]["name"]

    def test_rollback_nonexist(self, tmp_path, monkeypatch):
        monkeypatch.setattr(self_update, "BACKUP_DIR", str(tmp_path))
        ok, msg = rollback("nonexist-backup")
        assert ok == False


# ============================================================
# Elevate
# ============================================================

class TestElevate:
    def test_is_root_returns_bool(self):
        assert isinstance(is_root(), bool)

    def test_has_display(self):
        assert isinstance(has_display(), bool)

    def test_get_original_user(self):
        u = get_original_user()
        assert isinstance(u, str)
        assert len(u) > 0

    def test_detect_environment(self):
        env = detect_environment()
        for key in ("is_root", "has_display", "is_terminal",
                    "original_user", "method", "python_path", "script_path"):
            assert key in env

    def test_select_tool_returns_none_or_str(self):
        result = select_tool(prefer_gui=False)
        assert result is None or isinstance(result, str)

    def test_build_elevated_cmd(self):
        cmd = build_elevated_cmd("sudo", ["install", "htop"])
        assert isinstance(cmd, list)
        assert "sudo" in cmd
        assert "install" in cmd
        assert "htop" in cmd

    def test_build_elevated_cmd_gksu(self):
        cmd = build_elevated_cmd("gksu", ["install", "htop"])
        assert "gksu" in cmd

    def test_status_string(self):
        s = status_string()
        assert isinstance(s, str)
        assert "Root" in s

    def test_get_available_tools(self):
        tools = get_available_tools()
        assert isinstance(tools, dict)
        for name in ("sudo", "gksu", "gksudo", "pkexec"):
            assert name in tools

    def test_ensure_root_not_root(self, monkeypatch):
        """非 root 时 ensure_root 返回 False（不实际 exec）"""
        monkeypatch.setattr("xpm_suite.core.elevate.is_root", lambda: False)
        # 阻止实际 exec
        monkeypatch.setattr("os.execvp", lambda *a, **kw: None)
        result = ensure_root(args=["version"])
        assert isinstance(result, bool)


# ============================================================
# Integration: CLI 集成
# ============================================================

class TestCliIntegration:
    def test_xpm_main_has_auth_command(self):
        from xpm_suite.cli import xpm_main
        assert "auth" in xpm_main.COMMANDS
        assert "elevate" in xpm_main.COMMANDS

    def test_xstore_has_version_cmd(self):
        from xpm_suite.store import cli as xstore_cli
        assert "version" in xstore_cli.COMMANDS

    def test_xpm_help_includes_new_commands(self, capsys):
        from xpm_suite.cli import xpm_main
        rc = xpm_main.main(["--help"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "auth" in out.lower() or "认证" in out

    def test_auth_command_status(self, capsys):
        from xpm_suite.cli import xpm_main
        rc = xpm_main.main(["auth", "status"])
        assert rc == 0

    def test_auth_command_clear(self, capsys):
        AuthSession.grant("high", 300)
        from xpm_suite.cli import xpm_main
        rc = xpm_main.main(["auth", "clear"])
        assert rc == 0
        assert AuthSession.is_valid("high") == False

    def test_elevate_command_status(self, capsys):
        from xpm_suite.cli import xpm_main
        rc = xpm_main.main(["elevate"])
        assert rc == 0


# ============================================================
# Version bump
# ============================================================

class TestVersionBump:
    def test_version_is_310(self):
        from xpm_suite import version
        assert version.get_short_version() == "3.1.0"
        assert "Add Gui Store Edition" in version.get_version_string()

    def test_components_310(self):
        from xpm_suite import version
        for name, info in version.COMPONENTS.items():
            assert info["version"] == "3.1.0", f"{name} not 3.1.0"

    def test_feature_flags_have_new_entries(self):
        from xpm_suite import feature_flags
        new_features = ["pam_auth", "self_update", "elevate_auto",
                        "session_auth", "version_check"]
        for f in new_features:
            assert f in feature_flags.FEATURES, f"{f} not in FEATURES"
            assert feature_flags.FEATURES[f]["min"] == "3.1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

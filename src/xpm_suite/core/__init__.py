"""
XPM Suite 核心模块
"""

from .config import (
    detect_architecture, get_arch, set_arch, load_config, save_config,
    get_suite, get_downloader_config, get_gui_config, ensure_dirs,
)
from .statusdb import (
    StatusDB, PackageStatus, get_db, create_snapshot, list_snapshots,
    restore_snapshot,
)
from .installer import (
    InstallEngine, DependencyResolver, SourceIndex,
    InstallError, DependencyError, get_engine,
)
from .transaction import Transaction, atomic_write, atomic_remove
from .triggers import TriggerEngine, get_engine as get_trigger_engine
from .downloader import (
    ChunkDownloader, MirrorManager, get_downloader, get_mirror_manager,
    measure_all_mirrors, speedtest,
)
from .scripts_env import run_script, run_script_with_args
from .auth import (
    AuthAction, AuthSession, verify_action, require_auth,
    authenticate_user, detect_privilege, re_exec_with_privilege,
    install_pam_config, get_auth_log, auth_status,
)
from .self_update import (
    check_update, perform_update, rollback, list_backups,
    compare_versions, get_current_version, format_update_status,
    check_remote_version, VersionInfo,
)
from .elevate import (
    is_root, has_display, get_original_user, detect_environment,
    select_tool, build_elevated_cmd, re_exec, run_elevated,
    ensure_root, prompt_elevation, install_elevation_helpers,
    load_elevation_config, get_available_tools, status_string,
)

__all__ = [
    # config
    "detect_architecture", "get_arch", "set_arch", "load_config", "save_config",
    "get_suite", "get_downloader_config", "get_gui_config", "ensure_dirs",
    # statusdb
    "StatusDB", "PackageStatus", "get_db", "create_snapshot",
    "list_snapshots", "restore_snapshot",
    # installer
    "InstallEngine", "DependencyResolver", "SourceIndex",
    "InstallError", "DependencyError", "get_engine",
    # transaction
    "Transaction", "atomic_write", "atomic_remove",
    # triggers
    "TriggerEngine", "get_trigger_engine",
    # downloader
    "ChunkDownloader", "MirrorManager", "get_downloader",
    "get_mirror_manager", "measure_all_mirrors", "speedtest",
    # scripts
    "run_script", "run_script_with_args",
    # auth
    "AuthAction", "AuthSession", "verify_action", "require_auth",
    "authenticate_user", "detect_privilege", "re_exec_with_privilege",
    "install_pam_config", "get_auth_log", "auth_status",
    # self_update
    "check_update", "perform_update", "rollback", "list_backups",
    "compare_versions", "get_current_version", "format_update_status",
    "check_remote_version", "VersionInfo",
    # elevate
    "is_root", "has_display", "get_original_user", "detect_environment",
    "select_tool", "build_elevated_cmd", "re_exec", "run_elevated",
    "ensure_root", "prompt_elevation", "install_elevation_helpers",
    "load_elevation_config", "get_available_tools", "status_string",
]

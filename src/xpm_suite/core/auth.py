"""
XPM Suite - PAM 验证模块
用于验证安装/卸载/更新等操作是否由用户手动授权

设计思路:
- 优先使用系统 PAM (通过 python-pam 或 ctypes 调用 libpam)
- 降级方案: 提示输入密码并验证 (shadow/shadow-utils)
- 完全降级: 确认提示 (require manual confirmation)
- 支持 sudo/gksu/pkexec 提权检测
- 所有敏感操作必须先通过 verify_action() 才能执行
"""

import os
import sys
import subprocess
import getpass
import time
import hashlib
import json
import logging
from enum import Enum
from typing import Optional, Callable, Tuple

logger = logging.getLogger("xpm.auth")

# ============================================================
# 常量
# ============================================================

AUTH_DIR = "/etc/xpm/auth"
AUTH_DB = f"{AUTH_DIR}/auth.db"
AUTH_LOG = f"{AUTH_DIR}/auth.log"

# 需要授权的操作类型
class AuthAction(Enum):
    INSTALL   = "install"
    REMOVE    = "remove"
    UPDATE    = "update"
    UPGRADE   = "upgrade"
    PURGE     = "purge"
    LOCK      = "lock"
    UNLOCK    = "unlock"
    SNAPSHOT  = "snapshot"
    RESTORE   = "restore"
    SELF_UPGRADE = "self_upgrade"

# 每个操作的安全级别
ACTION_LEVEL = {
    AuthAction.INSTALL:       "medium",
    AuthAction.REMOVE:        "high",
    AuthAction.UPDATE:        "low",
    AuthAction.UPGRADE:       "high",
    AuthAction.PURGE:         "high",
    AuthAction.LOCK:          "medium",
    AuthAction.UNLOCK:        "medium",
    AuthAction.SNAPSHOT:      "medium",
    AuthAction.RESTORE:       "high",
    AuthAction.SELF_UPGRADE:  "critical",
}

# 授权有效期（秒）
AUTH_TTL = {
    "low":     300,   # 5 分钟
    "medium":  180,   # 3 分钟
    "high":    120,   # 2 分钟
    "critical": 60,   # 1 分钟
}

# ============================================================
# 会话管理 - 记录授权状态
# ============================================================

class AuthSession:
    """进程内授权会话，避免重复验证"""

    _session_token: Optional[str] = None
    _session_user: Optional[str] = None
    _session_expires: float = 0
    _session_level: str = "none"

    @classmethod
    def is_valid(cls, min_level: str = "low") -> bool:
        """检查当前会话是否有效且级别足够"""
        if not cls._session_token:
            return False
        if time.time() > cls._session_expires:
            cls.clear()
            return False
        level_order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        return level_order.get(cls._session_level, 0) >= level_order.get(min_level, 0)

    @classmethod
    def grant(cls, level: str, ttl: int):
        """授予授权"""
        cls._session_token = hashlib.sha256(
            f"{os.getpid()}{time.time()}{os.urandom(16).hex()}".encode()
        ).hexdigest()[:32]
        cls._session_user = os.environ.get("SUDO_USER", os.environ.get("USER", "root"))
        cls._session_expires = time.time() + ttl
        cls._session_level = level
        logger.info(f"Auth granted: user={cls._session_user} level={level} ttl={ttl}s")

    @classmethod
    def clear(cls):
        cls._session_token = None
        cls._session_user = None
        cls._session_expires = 0
        cls._session_level = "none"

    @classmethod
    def remaining_seconds(cls) -> int:
        if not cls._session_token:
            return 0
        return max(0, int(cls._session_expires - time.time()))


# ============================================================
# 提权检测
# ============================================================

def detect_privilege() -> dict:
    """
    检测当前进程的提权方式和状态

    返回:
        {
            "is_root": bool,
            "method": "root" | "sudo" | "gksu" | "pkexec" | "none",
            "original_user": str | None,
            "can_elevate": bool,
        }
    """
    uid = os.geteuid()
    is_root = (uid == 0)

    # 检测提权方式
    method = "none"
    orig_user = None

    if is_root:
        # 检查是不是 sudo
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user:
            method = "sudo"
            orig_user = sudo_user
        # 检查 gksu
        elif os.environ.get("GKSU_STARTED") == "1":
            method = "gksu"
            orig_user = os.environ.get("GKSU_USER", os.environ.get("USER"))
        # 检查 pkexec
        elif os.environ.get("PKEXEC_UID"):
            method = "pkexec"
            orig_user = os.environ.get("PKEXEC_USER", os.environ.get("USER"))
        else:
            method = "root"
            orig_user = os.environ.get("USER", "root")
    else:
        orig_user = os.environ.get("USER")

    # 能否提权
    can_elevate = False
    if not is_root:
        # 检查 sudo 是否可用
        try:
            r = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=2)
            can_elevate = (r.returncode == 0)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        # 检查 pkexec
        if not can_elevate:
            try:
                r = subprocess.run(["which", "pkexec"], capture_output=True, timeout=2)
                can_elevate = (r.returncode == 0)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

    return {
        "is_root": is_root,
        "method": method,
        "original_user": orig_user,
        "can_elevate": can_elevate,
    }


def re_exec_with_privilege(args: list) -> int:
    """
    重新以提权方式执行当前命令

    优先级: sudo > gksu > pkexec
    返回: 子进程退出码
    """
    script_path = os.path.abspath(sys.argv[0])
    full_args = [script_path] + args

    # 1. 尝试 sudo
    try:
        r = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=2)
        if r.returncode == 0:
            # 免密 sudo 可用
            return subprocess.run(["sudo", "--"] + full_args).returncode
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 2. 交互式 sudo（会提示输入密码）
    try:
        r = subprocess.run(["which", "sudo"], capture_output=True, timeout=2)
        if r.returncode == 0:
            print("  🔐 需要管理员权限，正在通过 sudo 提权...")
            return subprocess.run(["sudo", "--"] + full_args).returncode
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 3. 尝试 gksu / gksudo (GUI)
    for cmd in [["gksudo"], ["gksu"]]:
        try:
            r = subprocess.run(["which"] + cmd, capture_output=True, timeout=2)
            if r.returncode == 0:
                print(f"  🔐 通过 {' '.join(cmd)} 提权...")
                return subprocess.run(cmd + ["--"] + full_args).returncode
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # 4. 尝试 pkexec
    try:
        r = subprocess.run(["which", "pkexec"], capture_output=True, timeout=2)
        if r.returncode == 0:
            print("  🔐 通过 pkexec 提权...")
            return subprocess.run(["pkexec", "--"] + full_args).returncode
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    print("  ❌ 无法提权：sudo/gksu/pkexec 均不可用")
    print("     请手动以 root 身份运行此命令")
    return 1


# ============================================================
# PAM 验证
# ============================================================

def _try_pam_auth(service: str, username: str, password: str) -> bool:
    """
    通过 ctypes 直接调用 libpam 进行认证

    这是最可靠的方式，不依赖 python-pam 包
    """
    try:
        import ctypes
        import ctypes.util

        libpam_path = ctypes.util.find_library("pam") or "libpam.so.0"
        libpam = ctypes.CDLL(libpam_path)

        # 定义类型
        libpam.pam_start.argtypes = [
            ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
        ]
        libpam.pam_start.restype = ctypes.c_int
        libpam.pam_authenticate.argtypes = [ctypes.c_void_p, ctypes.c_int]
        libpam.pam_authenticate.restype = ctypes.c_int
        libpam.pam_acct_mgmt.argtypes = [ctypes.c_void_p, ctypes.c_int]
        libpam.pam_acct_mgmt.restype = ctypes.c_int
        libpam.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]
        libpam.pam_end.restype = ctypes.c_int

        # PAM 对话回调
        PAM_PROMPT_ECHO_OFF = 1
        PAM_PROMPT_ECHO_ON  = 2
        PAM_ERROR_MSG       = 3
        PAM_TEXT_INFO       = 4

        class PamMessage(ctypes.Structure):
            _fields_ = [
                ("msg_style", ctypes.c_int),
                ("msg", ctypes.c_char_p),
            ]

        class PamResponse(ctypes.Structure):
            _fields_ = [
                ("resp", ctypes.c_char_p),
                ("resp_retcode", ctypes.c_int),
            ]

        # 全局密码存储（回调中无法传参）
        _pam_password = password.encode("utf-8")

        @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int,
                          ctypes.POINTER(PamMessage),
                          ctypes.POINTER(ctypes.POINTER(PamResponse)),
                          ctypes.c_void_p)
        def pam_conv(nmsg, msg, resp, _appdata):
            responses = (PamResponse * nmsg)()
            for i in range(nmsg):
                style = msg[i].msg_style
                if style == PAM_PROMPT_ECHO_OFF:
                    responses[i].resp = ctypes.c_char_p(_pam_password)
                    responses[i].resp_retcode = 0
                elif style == PAM_PROMPT_ECHO_ON:
                    responses[i].resp = ctypes.c_char_p(b"")
                    responses[i].resp_retcode = 0
                else:
                    responses[i].resp = None
                    responses[i].resp_retcode = 0
            resp[0] = ctypes.cast(responses, ctypes.POINTER(PamResponse))
            return 0  # PAM_SUCCESS

        # 设置对话
        pamh = ctypes.c_void_p(0)
        conv = ctypes.Structure.__new__(
            type(ctypes.Structure)("PamConv", (ctypes.Structure,),
            {"_fields_": [("conv", ctypes.c_void_p), ("appdata_ptr", ctypes.c_void_p)]})
        )
        # 更简单的方式：直接用 ctypes
        class PamConv(ctypes.Structure):
            _fields_ = [
                ("conv", ctypes.c_void_p),
                ("appdata_ptr", ctypes.c_void_p),
            ]

        pc = PamConv(conv=ctypes.c_void_p(ctypes.cast(pam_conv, ctypes.c_void_p).value),
                      appdata_ptr=ctypes.c_void_p(0))

        # 启动 PAM
        _rc = 0
        _rc = libpam.pam_start(
            ctypes.c_char_p(service.encode("utf-8")),
            ctypes.c_char_p(username.encode("utf-8")),
            ctypes.cast(ctypes.byref(pc), ctypes.c_void_p),
            ctypes.byref(pamh)
        )
        if _rc != 0:
            return False

        try:
            # 认证
            _rc = libpam.pam_authenticate(pamh, 0)
            if _rc != 0:
                return False
            # 账户管理
            _rc = libpam.pam_acct_mgmt(pamh, 0)
            return (_rc == 0)
        finally:
            libpam.pam_end(pamh, _rc)

    except Exception as e:
        logger.debug(f"PAM ctypes 调用失败: {e}")
        return False


def _try_python_pam(service: str, username: str, password: str) -> bool:
    """尝试使用 python-pam 包"""
    try:
        import pam
        p = pam.pam()
        return p.authenticate(username, password, service=service)
    except ImportError:
        return False
    except Exception as e:
        logger.debug(f"python-pam 失败: {e}")
        return False


def _verify_password_shadow(username: str, password: str) -> bool:
    """
    降级方案：通过 shadow 文件验证密码
    仅 root 可读 /etc/shadow
    """
    try:
        import crypt
        import spwd
        try:
            entry = spwd.getspnam(username)
        except KeyError:
            # 用户不在 shadow 中，尝试 /etc/passwd
            import pwd
            try:
                pw_entry = pwd.getpwnam(username)
                if pw_entry.pw_passwd in ("x", "*", "!"):
                    return False
                # 直接用 crypt 验证
                return crypt.crypt(password, pw_entry.pw_passwd) == pw_entry.pw_passwd
            except KeyError:
                return False

        if not entry.sp_pwd:
            return False
        if entry.sp_pwd in ("*", "!", "!!"):
            return False

        # 用 crypt 验证
        hashed = crypt.crypt(password, entry.sp_pwd)
        return hashed == entry.sp_pwd
    except ImportError:
        return False
    except PermissionError:
        return False
    except Exception as e:
        logger.debug(f"shadow 验证失败: {e}")
        return False


def authenticate_user(service: str = "xpm",
                      username: Optional[str] = None,
                      reason: str = "") -> bool:
    """
    认证用户身份

    策略:
    1. 如果已经是 root (通过 sudo/gksu/pkexec)，认为已授权
    2. 尝试 PAM (ctypes → python-pam)
    3. 尝试 shadow 验证
    4. 全部失败 → 返回 False

    参数:
        service: PAM 服务名（对应 /etc/pam.d/xpm）
        username: 要认证的用户名（默认当前用户）
        reason: 认证原因（显示给用户）

    返回:
        True = 认证成功
    """
    # 如果已经是提权后的 root，直接通过
    priv = detect_privilege()
    if priv["is_root"]:
        logger.info(f"Already root via {priv['method']}, skip PAM")
        return True

    if username is None:
        username = priv.get("original_user") or os.environ.get("USER", "root")

    # 已经是 root 用户且非 sudo 场景
    if os.geteuid() == 0:
        return True

    # 尝试各种认证方式
    if reason:
        print(f"  🔐 {reason}")
    print(f"  👤 用户: {username}")

    for attempt in range(3):
        try:
            password = getpass.getpass(f"  密码 [{attempt+1}/3]: ")
        except (KeyboardInterrupt, EOFError):
            print("\n  ❌ 认证取消")
            return False

        if not password:
            print("  ⚠️ 密码不能为空")
            continue

        # 方式1: ctypes PAM
        if _try_pam_auth(service, username, password):
            logger.info(f"PAM auth success for {username}")
            return True

        # 方式2: python-pam
        if _try_python_pam(service, username, password):
            logger.info(f"python-pam auth success for {username}")
            return True

        # 方式3: shadow
        if _verify_password_shadow(username, password):
            logger.info(f"shadow auth success for {username}")
            return True

        print("  ❌ 密码错误")

    return False


# ============================================================
# 核心授权函数
# ============================================================

def verify_action(action: AuthAction,
                  target: str = "",
                  force: bool = False) -> Tuple[bool, str]:
    """
    验证一个敏感操作是否被授权执行

    这是所有安装/卸载/更新操作的统一入口检查。

    参数:
        action: 操作类型
        target: 操作目标（包名等，用于日志和显示）
        force: 是否跳过确认（仅限低安全级别）

    返回:
        (是否通过, 原因说明)

    流程:
        1. 检查是否 root / 已提权
        2. 检查会话是否已授权且未过期
        3. 根据安全级别要求认证或确认
        4. 通过后更新会话状态
    """
    level = ACTION_LEVEL.get(action, "medium")
    priv = detect_privilege()

    # 记录日志
    log_entry = {
        "timestamp": time.time(),
        "action": action.value,
        "target": target,
        "level": level,
        "user": priv.get("original_user", os.environ.get("USER", "?")),
        "method": priv.get("method", "none"),
    }

    # 1. 检查会话
    if AuthSession.is_valid(level):
        remaining = AuthSession.remaining_seconds()
        logger.info(f"Session valid: {action.value} {target} ({remaining}s left)")
        _write_auth_log(log_entry, "session_reused")
        return True, f"会话已授权 ({remaining}s)"

    # 2. 如果是 root 且通过 sudo/gksu/pkexec 提权，自动授权
    if priv["is_root"] and priv["method"] in ("sudo", "gksu", "pkexec"):
        ttl = AUTH_TTL.get(level, 120)
        AuthSession.grant(level, ttl)
        _write_auth_log(log_entry, "privileged")
        return True, f"已提权 ({priv['method']})"

    # 3. 如果是直接 root 登录
    if priv["is_root"] and priv["method"] == "root":
        ttl = AUTH_TTL.get(level, 120)
        AuthSession.grant(level, ttl)
        _write_auth_log(log_entry, "root")
        return True, "root 用户"

    # 4. 低安全级别 + force → 直接通过
    if level == "low" and force:
        ttl = AUTH_TTL.get("low", 300)
        AuthSession.grant("low", ttl)
        _write_auth_log(log_entry, "forced")
        return True, "强制模式"

    # 5. 需要认证
    reason_map = {
        AuthAction.INSTALL: f"安装软件包: {target}",
        AuthAction.REMOVE: f"卸载软件包: {target}",
        AuthAction.UPDATE: f"更新软件索引",
        AuthAction.UPGRADE: f"升级软件包: {target}",
        AuthAction.PURGE: f"彻底清除: {target}",
        AuthAction.LOCK: f"锁定包版本: {target}",
        AuthAction.UNLOCK: f"解锁包版本: {target}",
        AuthAction.SNAPSHOT: f"创建系统快照",
        AuthAction.RESTORE: f"恢复快照: {target}",
        AuthAction.SELF_UPGRADE: f"升级 XPM 自身",
    }
    reason = reason_map.get(action, f"执行 {action.value}: {target}")

    # 显示确认提示
    level_icon = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "⛔"}
    icon = level_icon.get(level, "⚪")
    print(f"\n  {icon} [{level.upper()}] 需要授权: {reason}")

    if level == "low":
        # 低安全级别 → 只需确认
        try:
            ans = input("  确认? [Y/n] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            _write_auth_log(log_entry, "cancelled")
            return False, "用户取消"
        if ans in ("", "y", "yes"):
            ttl = AUTH_TTL.get("low", 300)
            AuthSession.grant("low", ttl)
            _write_auth_log(log_entry, "confirmed")
            return True, "用户确认"
        _write_auth_log(log_entry, "declined")
        return False, "用户拒绝"

    # 中/高/严重 → 需要密码认证
    ok = authenticate_user(service="xpm", reason=reason)
    if ok:
        ttl = AUTH_TTL.get(level, 120)
        AuthSession.grant(level, ttl)
        _write_auth_log(log_entry, "authenticated")
        return True, "密码验证通过"
    else:
        _write_auth_log(log_entry, "auth_failed")
        return False, "认证失败"


def require_auth(action: AuthAction, target: str = ""):
    """
    装饰器/上下文用：要求授权，不通过则抛异常

    用法:
        ok, msg = verify_action(AuthAction.INSTALL, "htop")
        if not ok:
            print(f"  ❌ {msg}")
            return 1
    """
    ok, msg = verify_action(action, target)
    if not ok:
        raise PermissionError(f"操作未授权: {msg}")
    return True


# ============================================================
# 日志
# ============================================================

def _write_auth_log(entry: dict, result: str):
    """写入授权日志"""
    try:
        os.makedirs(AUTH_DIR, exist_ok=True)
        entry["result"] = result
        with open(AUTH_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except (PermissionError, OSError):
        pass


def get_auth_log(limit: int = 20) -> list:
    """读取最近的授权日志"""
    try:
        entries = []
        with open(AUTH_LOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries[-limit:]
    except FileNotFoundError:
        return []


# ============================================================
# PAM 服务配置生成
# ============================================================

def install_pam_config():
    """
    安装 PAM 服务配置文件 /etc/pam.d/xpm

    如果文件已存在则跳过。
    返回 True 表示配置就绪。
    """
    pam_dir = "/etc/pam.d"
    pam_file = f"{pam_dir}/xpm"

    if os.path.exists(pam_file):
        return True

    config = """# XPM Suite PAM 配置
# 允许本地用户通过密码认证执行包管理操作

auth    required    pam_unix.so
auth    optional    pam_permit.so

account required    pam_unix.so
account optional    pam_permit.so

password required   pam_unix.so

session required    pam_limits.so
session optional    pam_unix.so
"""

    try:
        os.makedirs(pam_dir, exist_ok=True)
        with open(pam_file, "w") as f:
            f.write(config)
        os.chmod(pam_file, 0o644)
        print(f"  ✅ PAM 配置已安装: {pam_file}")
        return True
    except PermissionError:
        print(f"  ⚠️ 无法写入 {pam_file}（需要 root）")
        print(f"     请手动创建该文件，内容见文档")
        return False


# ============================================================
# 公共 API
# ============================================================

def ensure_authorized(action: AuthAction, target: str = "") -> Tuple[bool, str]:
    """
    对外统一接口：检查 + 认证 + 提权

    完整流程:
    1. 检查当前是否已有授权会话
    2. 检查是否已提权 (root/sudo/gksu/pkexec)
    3. 尝试 PAM 密码认证
    4. 需要提权时自动 re-exec

    返回: (是否通过, 说明)
    """
    # 先检查
    ok, msg = verify_action(action, target)
    if ok:
        return True, msg

    # 如果没通过且不是 root，尝试提权后重新检查
    priv = detect_privilege()
    if not priv["is_root"] and priv["can_elevate"]:
        print(f"  🔐 需要管理员权限执行: {action.value} {target}")
        # 不自动 re-exec，让调用者决定是否重新启动
        # 返回特殊状态让 CLI 层处理
        return False, "NEED_ELEVATE"

    return False, msg


# ============================================================
# CLI 集成辅助
# ============================================================

def auth_status() -> str:
    """返回当前授权状态的人类可读描述"""
    priv = detect_privilege()
    session_valid = AuthSession.is_valid("low")
    remaining = AuthSession.remaining_seconds()

    lines = []
    lines.append(f"  👤 用户: {priv['original_user']}")
    lines.append(f"  🔑 Root: {'是' if priv['is_root'] else '否'}")
    lines.append(f"  🛡️ 提权方式: {priv['method']}")
    lines.append(f"  📋 可提权: {'是' if priv['can_elevate'] else '否'}")
    lines.append(f"  ✅ 会话有效: {'是' if session_valid else '否'}")
    if session_valid:
        lines.append(f"  ⏳ 剩余: {remaining}s")
    return "\n".join(lines)


# 允许直接运行测试
if __name__ == "__main__":
    print("=== XPM Auth Module Test ===\n")
    print("特权检测:")
    priv = detect_privilege()
    for k, v in priv.items():
        print(f"  {k}: {v}")

    print(f"\n{auth_status()}")

    print("\n测试安装授权 (Ctrl+C 取消):")
    try:
        ok, msg = verify_action(AuthAction.INSTALL, "htop")
        print(f"  结果: {'✅ 通过' if ok else '❌ 拒绝'} - {msg}")
    except KeyboardInterrupt:
        print("\n  取消")

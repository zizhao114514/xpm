"""
XPM Suite - 提权包装模块
统一 sudo / gksu / gksudo / pkexec 入口

设计:
- 检测当前权限状态
- 自动选择最佳提权方式
- 支持 GUI 环境的图形密码提示
- 提供 re_exec() 重新以特权运行当前进程
- 与 auth.py 配合：先认证 → 再提权 → 再执行
"""

import os
import sys
import subprocess
import shutil
import logging
from typing import Optional, List

logger = logging.getLogger("xpm.elevate")

# ============================================================
# 常量
# ============================================================

# 提权方式优先级（GUI 环境优先图形化）
GUI_PRIORITY = ["gksudo", "gksu", "pkexec", "sudo"]
CLI_PRIORITY = ["sudo", "pkexec", "gksu", "gksudo"]

# 各工具的命令行格式
TOOL_ARGS = {
    "sudo":    ["sudo", "--preserve-env=PATH,USER,HOME"],
    "gksu":    ["gksu", "--preserve-env"],
    "gksudo":  ["gksudo", "--preserve-env"],
    "pkexec":  ["pkexec"],
}

# ============================================================
# 环境检测
# ============================================================

def is_root() -> bool:
    """当前是否为 root"""
    return os.geteuid() == 0


def is_in_terminal() -> bool:
    """是否在终端中运行"""
    return sys.stdin.isatty() and sys.stdout.isatty()


def has_display() -> bool:
    """是否有 DISPLAY（GUI 环境）"""
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def get_original_user() -> str:
    """获取原始用户名（提权前的用户）"""
    for key in ["SUDO_USER", "GKSU_USER", "PKEXEC_USER", "USER"]:
        val = os.environ.get(key)
        if val and val != "root":
            return val
    return os.environ.get("USER", "unknown")


def detect_environment() -> dict:
    """检测完整运行环境"""
    return {
        "is_root": is_root(),
        "has_display": has_display(),
        "is_terminal": is_in_terminal(),
        "original_user": get_original_user(),
        "method": _detect_method(),
        "python_path": sys.executable,
        "script_path": _get_script_path(),
    }


def _detect_method() -> str:
    """检测当前提权方式"""
    if os.geteuid() != 0:
        return "none"
    if os.environ.get("SUDO_USER"):
        return "sudo"
    if os.environ.get("GKSU_STARTED") == "1" or os.environ.get("GKSU_USER"):
        return "gksu"
    if os.environ.get("PKEXEC_UID"):
        return "pkexec"
    return "root"


def _get_script_path() -> str:
    """获取当前脚本路径"""
    # sys.argv[0] 可能是相对路径
    path = os.path.abspath(sys.argv[0])
    if os.path.exists(path):
        return path
    # 尝试从 PATH 找
    for d in os.environ.get("PATH", "").split(":"):
        candidate = os.path.join(d, sys.argv[0])
        if os.path.exists(candidate):
            return candidate
    return sys.argv[0]


# ============================================================
# 工具可用性检测
# ============================================================

def _check_tool(name: str) -> bool:
    """检查提权工具是否可用"""
    return shutil.which(name) is not None


def _check_sudo_nopasswd() -> bool:
    """检查 sudo 是否免密"""
    try:
        r = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True, timeout=2
        )
        return (r.returncode == 0)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_available_tools() -> dict:
    """返回所有可用工具及其状态"""
    tools = {}
    for name in ["sudo", "gksu", "gksudo", "pkexec"]:
        available = _check_tool(name)
        tools[name] = {
            "available": available,
            "nopasswd": False,
        }
        if name == "sudo" and available:
            tools[name]["nopasswd"] = _check_sudo_nopasswd()
    return tools


# ============================================================
# 核心提权函数
# ============================================================

def select_tool(prefer_gui: Optional[bool] = None) -> Optional[str]:
    """
    选择最佳提权工具

    参数:
        prefer_gui: 是否优先图形化工具
                   None = 自动检测（有 DISPLAY 则 GUI 优先）

    返回:
        工具名 或 None（无可用工具）
    """
    if prefer_gui is None:
        prefer_gui = has_display()

    priority = GUI_PRIORITY if prefer_gui else CLI_PRIORITY

    for tool in priority:
        if _check_tool(tool):
            return tool

    return None


def build_elevated_cmd(tool: str, args: Optional[List[str]] = None) -> List[str]:
    """
    构建提权后的完整命令

    参数:
        tool: 提权工具名
        args: 要传递的参数列表

    返回:
        完整命令列表（可直接传给 subprocess）
    """
    base = TOOL_ARGS.get(tool, [tool]).copy()
    script = _get_script_path()
    cmd = base + [script]

    if args:
        cmd += args

    return cmd


def re_exec(args: Optional[List[str]] = None,
            prefer_gui: Optional[bool] = None) -> int:
    """
    重新以特权执行当前命令

    这是核心函数：检测到非 root 时，自动选择工具并 re-exec。

    参数:
        args: 传递给新进程的参数（默认使用 sys.argv[1:]）
        prefer_gui: 是否优先图形化工具

    返回:
        子进程退出码（成功时不会返回，直接 exec）

    注意:
        如果提权成功，当前进程会被替换（exec），不会返回。
        只有失败时才会返回错误码。
    """
    if is_root():
        return 0  # 已经是 root，无需提权

    if args is None:
        args = sys.argv[1:]

    tool = select_tool(prefer_gui)
    if not tool:
        print("  ❌ 无法提权：未找到 sudo/gksu/pkexec", file=sys.stderr)
        print("     请手动以 root 身份运行", file=sys.stderr)
        return 127

    cmd = build_elevated_cmd(tool, args)

    tool_icon = {"sudo": "🔐", "gksu": "🖥️", "gksudo": "🖥️", "pkexec": "🔑"}
    icon = tool_icon.get(tool, "🔐")
    print(f"  {icon} 通过 {tool} 提权...")

    try:
        # 使用 exec 替换当前进程
        os.execvp(cmd[0], cmd)
    except OSError as e:
        print(f"  ❌ 提权失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"  ❌ 意外错误: {e}", file=sys.stderr)
        return 1

    return 1  # 不应该到这里


def run_elevated(tool: str, args: List[str]) -> int:
    """
    以特权运行命令（不替换当前进程）

    用于需要临时提权执行单个命令的场景。
    """
    cmd = build_elevated_cmd(tool, args)
    try:
        result = subprocess.run(cmd)
        return result.returncode
    except (FileNotFoundError, OSError) as e:
        print(f"  ❌ 执行失败: {e}", file=sys.stderr)
        return 1


# ============================================================
# 高级接口
# ============================================================

def ensure_root(args: Optional[List[str]] = None,
                prefer_gui: Optional[bool] = None) -> bool:
    """
    确保以 root 运行

    如果不是 root：
    1. 尝试自动提权（re-exec）
    2. 成功则不会返回（进程被替换）
    3. 失败则返回 False

    如果是 root，直接返回 True。

    用法:
        if not ensure_root():
            sys.exit(1)
        # 以下代码保证以 root 运行
    """
    if is_root():
        return True

    code = re_exec(args, prefer_gui)
    if code == 0:
        # re-exec 成功，当前进程已被替换
        # 这行理论上不会执行，但保险起见
        sys.exit(0)

    return False


def prompt_elevation(reason: str = "") -> bool:
    """
    提示用户提权并选择方式

    显示可用工具菜单，让用户选择。
    返回 True 表示提权成功（进程会被替换）。
    """
    tools = get_available_tools()
    available = [(name, info) for name, info in tools.items() if info["available"]]

    if not available:
        print("  ❌ 没有可用的提权工具")
        return False

    if reason:
        print(f"  🔐 需要管理员权限: {reason}")

    print("  选择提权方式:")
    for i, (name, info) in enumerate(available, 1):
        extra = ""
        if info["nopasswd"]:
            extra = " (免密)"
        elif name in ("gksu", "gksudo"):
            extra = " (图形密码框)"
        print(f"    [{i}] {name}{extra}")

    try:
        choice = input("  选择 [1]: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n  取消")
        return False

    if not choice:
        choice = "1"

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(available):
            tool = available[idx][0]
            code = re_exec(prefer_gui=(tool in ("gksu", "gksudo")))
            return (code == 0)
    except ValueError:
        pass

    print("  ❌ 无效选择")
    return False


# ============================================================
# 安装脚本辅助
# ============================================================

def install_elevation_helpers():
    """
    安装提权相关的辅助配置

    - 创建 /etc/xpm/elevate.conf
    - 设置默认提权偏好
    """
    config_dir = "/etc/xpm"
    config_file = f"{config_dir}/elevate.conf"

    try:
        os.makedirs(config_dir, exist_ok=True)
    except PermissionError:
        print(f"  ⚠️ 无法创建 {config_dir}")
        return False

    config = {
        "prefer_gui": has_display(),
        "default_tool": select_tool() or "sudo",
        "fallback_chain": GUI_PRIORITY if has_display() else CLI_PRIORITY,
        "sudo_keep_env": ["PATH", "USER", "HOME", "DISPLAY", "XAUTHORITY"],
    }

    try:
        import json
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        os.chmod(config_file, 0o644)
        print(f"  ✅ 提权配置已写入: {config_file}")
        return True
    except (PermissionError, OSError) as e:
        print(f"  ⚠️ 写入失败: {e}")
        return False


def load_elevation_config() -> dict:
    """加载提权配置"""
    config_file = "/etc/xpm/elevate.conf"
    default = {
        "prefer_gui": has_display(),
        "default_tool": "sudo",
        "fallback_chain": GUI_PRIORITY if has_display() else CLI_PRIORITY,
    }
    try:
        import json
        with open(config_file) as f:
            user_cfg = json.load(f)
        default.update(user_cfg)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        pass
    return default


# ============================================================
# 状态显示
# ============================================================

def status_string() -> str:
    """返回人类可读的状态"""
    env = detect_environment()
    lines = []
    lines.append(f"  👤 原始用户: {env['original_user']}")
    lines.append(f"  🔑 Root: {'是' if env['is_root'] else '否'}")
    lines.append(f"  🛡️ 提权方式: {env['method']}")
    lines.append(f"  🖥️ 显示服务: {'有 (GUI)' if env['has_display'] else '无 (CLI)'}")
    lines.append(f"  📟 终端: {'是' if env['is_terminal'] else '否'}")

    tools = get_available_tools()
    available = [n for n, i in tools.items() if i["available"]]
    lines.append(f"  🔧 可用工具: {', '.join(available) if available else '无'}")

    return "\n".join(lines)


# ============================================================
# 直接运行测试
# ============================================================

if __name__ == "__main__":
    print("=== XPM Elevate Module Test ===\n")

    print("环境检测:")
    print(status_string())

    print(f"\n脚本路径: {_get_script_path()}")
    print(f"Python: {sys.executable}")

    print("\n可用工具:")
    tools = get_available_tools()
    for name, info in tools.items():
        icon = "✅" if info["available"] else "❌"
        extra = " (免密)" if info["nopasswd"] else ""
        print(f"  {icon} {name}{extra}")

    selected = select_tool()
    print(f"\n推荐工具: {selected or '无'}")

"""
XPM Suite maintainer scripts 执行环境
模拟 dpkg 调用 preinst/postinst/prerm/postrm 时的完整环境变量
"""

import os, subprocess, tempfile, re
from typing import Optional, Dict


def build_script_env(pkg_name: str, pkg_version: str, pkg_arch: str,
                     action: str, old_version: str = "",
                     old_arch: str = "", **extra) -> Dict[str, str]:
    """构建 maintainer script 执行环境"""
    env = os.environ.copy()

    env["DPKG_ADMINDIR"] = "/var/lib/dpkg"
    env["DPKG_DATADIR"] = "/usr/share/dpkg"
    env["DPKG_INFODIR"] = "/var/lib/dpkg/info"
    env["DPKG_MAINTSCRIPT_NAME"] = action
    env["DPKG_MAINTSCRIPT_PACKAGE"] = pkg_name
    env["DPKG_MAINTSCRIPT_ARCH"] = pkg_arch
    env["DPKG_VERSION"] = "1.22.0"
    env["DPKG_RUNNING_VERSION"] = "1.22.0"
    env["DPKG_ROOT"] = "/"
    env["DPKG_FORCE"] = ""
    env["DPKG_OFFLINE"] = "0"

    env["DPKG_MAINTSCRIPT_PACKAGE_REFCOUNT"] = "1"
    env["DPKG_NEW_CONFFILE"] = ""
    env["DPKG_OLD_CONFFILE"] = ""

    env["DPKG_HOST_ARCH"] = pkg_arch
    env["DPKG_HOST_OS"] = "linux"
    env["DPKG_HOST_TYPE"] = f"{pkg_arch}-linux-gnu"

    if old_version:
        cmp = _version_compare(old_version, pkg_version)
        env["DPKG_UPGRADE"] = "1" if cmp < 0 else "0"
        env["DPKG_DOWNGRADE"] = "1" if cmp > 0 else "0"
    else:
        env["DPKG_UPGRADE"] = "0"
        env["DPKG_DOWNGRADE"] = "0"

    if action == "triggered":
        env["DPKG_TRIGGER_NAME"] = extra.get("trigger_name", "")
    else:
        env["DPKG_TRIGGER_NAME"] = ""

    env["DPKG_CONFIG_FILE"] = "/etc/dpkg/dpkg.cfg"

    env["XPM_VERSION"] = "3.0.0"
    env["XPM_MANAGER"] = "xpm-suite"

    for k, v in extra.items():
        if k.upper().startswith(("DPKG_", "XPM_")):
            env[k.upper()] = str(v)

    return env


def _version_compare(v1: str, v2: str) -> int:
    """Debian 版本比较，返回 -1/0/1"""
    def parse(v):
        v = str(v).strip()
        if "-" in v:
            ver, rev = v.rsplit("-", 1)
            try:
                rev = int(rev)
            except ValueError:
                rev = 0
        else:
            ver, rev = v, 0
        # 把版本字符串转为可比较的元组
        parts = []
        for chunk in re.split(r"([0-9]+)", ver):
            if chunk == "" or chunk is None:
                continue
            if chunk.isdigit():
                parts.append((1, int(chunk)))
            else:
                parts.append((0, chunk))
        while len(parts) < 4:
            parts.append((0, ""))
        return (tuple(parts[:4]), rev)

    a, b = parse(v1), parse(v2)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def run_script(script_path: str, pkg_name: str, pkg_version: str,
              pkg_arch: str, action: str, **extra) -> tuple:
    """执行 maintainer script"""
    if not os.path.exists(script_path):
        return (0, "", "no script (skipped)")
    env = build_script_env(pkg_name, pkg_version, pkg_arch, action, **extra)
    try:
        r = subprocess.run(
            ["sh", script_path],
            capture_output=True, text=True, timeout=120, env=env
        )
        return (r.returncode, r.stdout, r.stderr)
    except subprocess.TimeoutExpired:
        return (-1, "", "script timeout (120s)")
    except Exception as e:
        return (-1, "", str(e))


def run_script_with_args(script_path: str, args: list, pkg_name: str,
                         pkg_version: str, pkg_arch: str, **extra) -> tuple:
    """带参数执行"""
    if not os.path.exists(script_path):
        return (0, "", "no script (skipped)")
    action = os.path.basename(script_path).split(".")[-1]
    env = build_script_env(pkg_name, pkg_version, pkg_arch, action, **extra)
    try:
        r = subprocess.run(
            ["sh", script_path] + [str(a) for a in args],
            capture_output=True, text=True, timeout=120, env=env
        )
        return (r.returncode, r.stdout, r.stderr)
    except subprocess.TimeoutExpired:
        return (-1, "", "script timeout (120s)")
    except Exception as e:
        return (-1, "", str(e))


SCRIPT_TEMPLATES = {
    "postinst_ldconfig": """#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    ldconfig 2>/dev/null || true
fi
""",
    "postinst_fontconfig": """#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    fc-cache -f 2>/dev/null || true
fi
""",
    "postinst_mandb": """#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    mandb 2>/dev/null || true
fi
""",
    "postinst_initramfs": """#!/bin/sh
set -e
if [ -x /usr/sbin/update-initramfs ]; then
    update-initramfs -u 2>/dev/null || true
fi
""",
}


def write_script_template(template_name: str, dest_path: str, **kwargs):
    """将模板写入文件"""
    if template_name not in SCRIPT_TEMPLATES:
        raise ValueError(f"未知模板: {template_name}")
    content = SCRIPT_TEMPLATES[template_name]
    for k, v in kwargs.items():
        content = content.replace("{" + k + "}", str(v))
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    with open(dest_path, "w") as f:
        f.write(content)
    os.chmod(dest_path, 0o755)


def verify_env(pkg_name: str = "test", action: str = "postinst") -> dict:
    """验证所有 DPKG_ 变量是否正确设置"""
    env = build_script_env(pkg_name, "1.0", "arm64", action)
    required = [
        "DPKG_ADMINDIR", "DPKG_INFODIR", "DPKG_MAINTSCRIPT_NAME",
        "DPKG_MAINTSCRIPT_PACKAGE", "DPKG_MAINTSCRIPT_ARCH",
        "DPKG_VERSION", "DPKG_ROOT", "DPKG_HOST_ARCH",
    ]
    results = {}
    for var in required:
        results[var] = env.get(var, "MISSING")
    return results


if __name__ == "__main__":
    print("=== DPKG_ 环境变量验证 ===")
    results = verify_env("htop", "postinst")
    for k, v in results.items():
        icon = "✅" if v != "MISSING" else "❌"
        print(f"  {icon} {k:<30} = {v}")

    print(f"\n=== 版本比较测试 ===")
    tests = [("1.0", "2.0", -1), ("2.0", "1.0", 1), ("1.0-1", "1.0-2", -1)]
    for a, b, expected in tests:
        actual = _version_compare(a, b)
        icon = "✅" if actual == expected else "❌"
        print(f"  {icon} {a} vs {b}: {actual} (期望 {expected})")

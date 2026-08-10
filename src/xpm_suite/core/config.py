"""
XPM Suite 配置管理
持久化架构探测结果 + 源列表 + 用户偏好
"""

import os, json, subprocess
from pathlib import Path

CONFIG_DIR = Path("/etc/xpm")
CONFIG_FILE = CONFIG_DIR / "config.json"
CACHE_DIR = Path("/var/cache/xpm")
STATE_DIR = Path("/var/lib/xpm")

DEFAULT_CONFIG = {
    "architecture": None,
    "arch_source": None,
    "default_suite": "trixie",
    "sources_dir": "/etc/xpm/sources.list.d",
    "cache_dir": "/var/cache/xpm",
    "state_dir": "/var/lib/xpm",
    "downloader": {
        "threads": 4,
        "chunk_size": 1048576,
        "timeout": 30,
        "retry": 5,
        "backoff_base": 2,
        "bandwidth_limit": 0,
    },
    "gui": {
        "theme": "dark",
        "window_width": 1000,
        "window_height": 700,
        "card_columns": 3,
    },
    "features_checked": {},
}


def ensure_dirs():
    for d in [CONFIG_DIR, CACHE_DIR, STATE_DIR, Path("/etc/xpm/sources.list.d")]:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            pass


def detect_architecture(force=False):
    if not force:
        cfg = load_config()
        if cfg.get("architecture"):
            return cfg["architecture"]

    arch = None
    source = None

    # 方法1: dpkg
    try:
        out = subprocess.run(
            ["dpkg", "--print-architecture"],
            capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0 and out.stdout.strip():
            arch = out.stdout.strip()
            source = "dpkg --print-architecture"
    except Exception:
        pass

    # 方法2: uname -m
    if not arch:
        try:
            out = subprocess.run(
                ["uname", "-m"],
                capture_output=True, text=True, timeout=5
            )
            m = out.stdout.strip()
            mapping = {
                "x86_64": "amd64", "aarch64": "arm64", "armv7l": "armhf",
                "armv6l": "armel", "i686": "i386", "i386": "i386",
                "loongarch64": "loong64", "riscv64": "riscv64",
                "ppc64le": "ppc64el", "s390x": "s390x",
            }
            if m in mapping:
                arch = mapping[m]
                source = f"uname -m -> {m}"
        except Exception:
            pass

    # 方法3: /proc/cpuinfo
    if not arch:
        try:
            with open("/proc/cpuinfo") as f:
                content = f.read().lower()
            if "aarch64" in content or "armv8" in content:
                arch = "arm64"
                source = "/proc/cpuinfo"
            elif "armv7" in content:
                arch = "armhf"
                source = "/proc/cpuinfo"
            elif "loongarch" in content:
                arch = "loong64"
                source = "/proc/cpuinfo"
        except Exception:
            pass

    # 兜底
    if not arch:
        arch = "amd64"
        source = "fallback"

    cfg = load_config()
    cfg["architecture"] = arch
    cfg["arch_source"] = source
    save_config(cfg)
    return arch


def load_config():
    ensure_dirs()
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cfg = {}

    def merge(default, user):
        for k, v in default.items():
            if k not in user:
                user[k] = v
            elif isinstance(v, dict) and isinstance(user.get(k), dict):
                merge(v, user[k])
        return user

    return merge(DEFAULT_CONFIG, cfg)


def save_config(cfg):
    ensure_dirs()
    try:
        tmp = CONFIG_FILE.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp, CONFIG_FILE)
    except PermissionError:
        pass


def get_arch():
    cfg = load_config()
    if not cfg.get("architecture"):
        return detect_architecture()
    return cfg["architecture"]


def get_suite():
    return load_config().get("default_suite", "trixie")


def get_downloader_config():
    return load_config().get("downloader", DEFAULT_CONFIG["downloader"])


def get_gui_config():
    return load_config().get("gui", DEFAULT_CONFIG["gui"])


def set_arch(arch):
    valid = {"amd64","arm64","armhf","armel","i386","loong64","riscv64","ppc64el","s390x"}
    if arch not in valid:
        raise ValueError(f"无效架构: {arch}, 可选: {', '.join(sorted(valid))}")
    cfg = load_config()
    cfg["architecture"] = arch
    cfg["arch_source"] = "user-override"
    save_config(cfg)
    return arch


if __name__ == "__main__":
    print(f"架构: {detect_architecture()}")
    print(f"配置: {json.dumps(load_config(), indent=2, ensure_ascii=False)}")

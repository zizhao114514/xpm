"""
XPM Suite - 版本检测与自更新模块

功能:
- 检测当前 XPM / X-Store 版本
- 从远程源检查最新版本
- 自动下载并更新自身
- 支持回滚到上一版本
- 与 PAM 认证集成（self_upgrade 需要 critical 级别授权）
"""

import os
import sys
import json
import hashlib
import subprocess
import tempfile
import time
import logging
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("xpm.self_update")

# ============================================================
# 常量
# ============================================================

# 版本检查源（可配置）
DEFAULT_UPDATE_URL = "https://api.github.com/repos/zizhao114514/xpm/releases/latest"
FALLBACK_UPDATE_URL = "https://raw.githubusercontent.com/zizhao114514/xpm/main/VERSION"

# 当前版本（与 version.py 保持一致）
CURRENT_VERSION = "3.1.1"
CURRENT_CODENAME = "Add Gui Store Edition"

# 更新缓存
UPDATE_CACHE_DIR = "/var/cache/xpm/updates"
UPDATE_CACHE_FILE = f"{UPDATE_CACHE_DIR}/latest.json"
UPDATE_CACHE_TTL = 3600  # 1 小时

# 备份目录
BACKUP_DIR = "/var/lib/xpm/backups"

# ============================================================
# 版本数据结构
# ============================================================

@dataclass
class VersionInfo:
    """版本信息"""
    version: str
    codename: str = ""
    release_date: str = ""
    changelog: str = ""
    download_url: str = ""
    sha256: str = ""
    size: int = 0
    min_python: str = "3.8"
    source: str = "unknown"  # github | http | local

    def __str__(self):
        s = f"v{self.version}"
        if self.codename:
            s += f' "{self.codename}"'
        if self.release_date:
            s += f" ({self.release_date})"
        return s

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "codename": self.codename,
            "release_date": self.release_date,
            "changelog": self.changelog,
            "download_url": self.download_url,
            "sha256": self.sha256,
            "size": self.size,
            "min_python": self.min_python,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VersionInfo":
        return cls(
            version=d.get("version", "0.0.0"),
            codename=d.get("codename", ""),
            release_date=d.get("release_date", ""),
            changelog=d.get("changelog", ""),
            download_url=d.get("download_url", ""),
            sha256=d.get("sha256", ""),
            size=d.get("size", 0),
            min_python=d.get("min_python", "3.8"),
            source=d.get("source", "unknown"),
        )


# ============================================================
# 版本比较
# ============================================================

def parse_version_str(vstr: str) -> Tuple[int, int, int]:
    """解析版本字符串 → (major, minor, patch)"""
    import re
    # 处理 "3.0.0" / "3.0-0" / "v3.0.0" / "3.0.0-rc1"
    m = re.match(r"v?(\d+)\.(\d+)(?:\.(\d+))?", str(vstr))
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def compare_versions(v1: str, v2: str) -> int:
    """
    比较两个版本号
    返回: 1 if v1 > v2, 0 if equal, -1 if v1 < v2
    """
    a = parse_version_str(v1)
    b = parse_version_str(v2)
    if a > b: return 1
    if a == b: return 0
    return -1


def get_current_version() -> str:
    """获取当前安装的 XPM Suite 版本"""
    # 优先从 package 读
    try:
        from ..version import get_short_version
        return get_short_version()
    except ImportError:
        pass
    # 从文件读
    version_file = "/etc/xpm/VERSION"
    try:
        with open(version_file) as f:
            return f.read().strip()
    except FileNotFoundError:
        pass
    return CURRENT_VERSION


def get_current_codename() -> str:
    try:
        from ..version import get_codename
        return get_codename()
    except ImportError:
        pass
    return CURRENT_CODENAME


# ============================================================
# 远程版本检查
# ============================================================

def _fetch_url(url: str, timeout: int = 10) -> Optional[str]:
    """简单的 URL 获取（不依赖外部库）"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "XPM-Suite/3.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug(f"URL fetch failed [{url}]: {e}")
        return None


def _parse_github_release(json_text: str) -> Optional[VersionInfo]:
    """解析 GitHub API 响应"""
    try:
        data = json.loads(json_text)
        tag = data.get("tag_name", "")
        # tag: "v3.1.0" 或 "XPM Suite v3.1.0"
        version = tag.replace("XPM Suite v", "").replace("v", "").strip()

        # 提取 changelog
        body = data.get("body", "")
        changelog = body[:1000] if body else ""

        # 找 .deb 资产
        assets = data.get("assets", [])
        download_url = ""
        size = 0
        sha256 = ""
        for a in assets:
            name = a.get("name", "")
            if name.endswith(".deb"):
                download_url = a.get("browser_download_url", "")
                size = a.get("size", 0)
                break

        return VersionInfo(
            version=version,
            codename="",
            release_date=data.get("published_at", "")[:10],
            changelog=changelog,
            download_url=download_url,
            sha256=sha256,
            size=size,
            source="github",
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.debug(f"GitHub parse failed: {e}")
        return None


def _parse_simple_version(text: str) -> Optional[VersionInfo]:
    """解析简单版本文件格式:
    VERSION=3.1.0
    CODENAME=Something Edition
    URL=https://...
    SHA256=abc...
    """
    info = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            info[k.strip().upper()] = v.strip()

    if "VERSION" not in info:
        return None

    return VersionInfo(
        version=info["VERSION"],
        codename=info.get("CODENAME", ""),
        download_url=info.get("URL", ""),
        sha256=info.get("SHA256", ""),
        source="http",
    )


def check_remote_version(cache: bool = True) -> Optional[VersionInfo]:
    """
    从远程检查最新版本

    参数:
        cache: 是否使用缓存（1小时内不重复请求）

    返回:
        VersionInfo 或 None（检查失败）
    """
    # 检查缓存
    if cache:
        try:
            age = time.time() - os.path.getmtime(UPDATE_CACHE_FILE)
            if age < UPDATE_CACHE_TTL:
                with open(UPDATE_CACHE_FILE) as f:
                    return VersionInfo.from_dict(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass

    # 尝试 GitHub API
    text = _fetch_url(DEFAULT_UPDATE_URL)
    info = None
    if text:
        info = _parse_github_release(text)

    # 降级到简单版本文件
    if not info:
        text2 = _fetch_url(FALLBACK_UPDATE_URL)
        if text2:
            info = _parse_simple_version(text2)

    if info:
        # 缓存结果
        try:
            os.makedirs(UPDATE_CACHE_DIR, exist_ok=True)
            with open(UPDATE_CACHE_FILE, "w") as f:
                json.dump(info.to_dict(), f, indent=2)
        except (PermissionError, OSError):
            pass

    return info


# ============================================================
# 更新状态
# ============================================================

def check_update() -> Dict[str, Any]:
    """
    检查更新，返回状态字典

    返回:
        {
            "current": "3.0.0",
            "latest": "3.1.0" | None,
            "update_available": True/False,
            "changelog": "...",
            "download_url": "...",
            "size": 12345,
        }
    """
    current = get_current_version()
    latest = check_remote_version()

    result = {
        "current": current,
        "latest": latest.version if latest else None,
        "update_available": False,
        "changelog": "",
        "download_url": "",
        "size": 0,
    }

    if latest:
        cmp = compare_versions(latest.version, current)
        result["update_available"] = (cmp == 1)
        result["changelog"] = latest.changelog
        result["download_url"] = latest.download_url
        result["size"] = latest.size
        result["release_date"] = latest.release_date

    return result


# ============================================================
# 下载 + 校验 + 安装
# ============================================================

def _download_file(url: str, dest: str, progress_cb=None) -> bool:
    """下载文件到指定路径"""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "XPM-Suite/3.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", "0"))
            downloaded = 0
            chunk_size = 64 * 1024
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total:
                        pct = int(downloaded * 100 / total)
                        progress_cb(pct, 100, os.path.basename(dest))
        return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


def _verify_sha256(path: str, expected: str) -> bool:
    """验证 SHA256"""
    if not expected:
        return True  # 无校验值则跳过
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(64 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest().lower() == expected.lower()


def _backup_current() -> Optional[str]:
    """备份当前安装"""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_path = f"{BACKUP_DIR}/xpm-suite-{timestamp}"

        # 备份关键文件
        import shutil
        src = "/usr/local/share/xpm"
        if os.path.isdir(src):
            shutil.copytree(src, f"{backup_path}-share", dirs_exist_ok=True)
        for bin_name in ["xpm", "xstore", "xstore-gui"]:
            src_bin = f"/usr/local/bin/{bin_name}"
            if os.path.exists(src_bin):
                os.makedirs(backup_path, exist_ok=True)
                shutil.copy2(src_bin, f"{backup_path}-{bin_name}")

        return backup_path
    except (PermissionError, OSError) as e:
        logger.warning(f"Backup failed: {e}")
        return None


def _install_deb(path: str) -> bool:
    """安装 .deb 包（使用 dpkg 或 XPM 自身）"""
    try:
        # 优先用 dpkg 安装自身更新
        r = subprocess.run(
            ["dpkg", "-i", path],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0:
            return True
        # dpkg 失败时尝试修复
        subprocess.run(["dpkg", "--configure", "-a"], capture_output=True, timeout=60)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.error(f"dpkg install failed: {e}")
        return False


def perform_update(download_url: str,
                   expected_sha256: str = "",
                   progress_cb=None) -> Tuple[bool, str]:
    """
    执行完整更新流程: 下载 → 校验 → 备份 → 安装

    参数:
        download_url: .deb 下载地址
        expected_sha256: 预期 SHA256（空则跳过校验）
        progress_cb: 进度回调 (pct, total, msg)

    返回:
        (是否成功, 说明)
    """
    if not download_url:
        return False, "无下载地址"

    os.makedirs(UPDATE_CACHE_DIR, exist_ok=True)
    tmp_path = f"{UPDATE_CACHE_DIR}/xpm-suite-update.deb"

    # 1. 下载
    if progress_cb:
        progress_cb(0, 100, "下载更新...")
    if not _download_file(download_url, tmp_path, progress_cb):
        return False, "下载失败"

    # 2. 校验
    if progress_cb:
        progress_cb(80, 100, "校验...")
    if expected_sha256 and not _verify_sha256(tmp_path, expected_sha256):
        os.remove(tmp_path)
        return False, "校验失败 (SHA256 不匹配)"

    # 3. 备份
    if progress_cb:
        progress_cb(90, 100, "备份当前版本...")
    backup = _backup_current()
    if backup:
        logger.info(f"Backup created: {backup}")

    # 4. 安装
    if progress_cb:
        progress_cb(95, 100, "安装...")
    if not _install_deb(tmp_path):
        return False, "安装失败（尝试手动: dpkg -i " + tmp_path + "）"

    # 5. 清理
    try:
        os.remove(tmp_path)
    except OSError:
        pass

    if progress_cb:
        progress_cb(100, 100, "完成!")

    return True, "更新成功! 请重启终端使更改生效"


# ============================================================
# 回滚
# ============================================================

def list_backups() -> list:
    """列出可用备份"""
    try:
        backups = []
        for d in sorted(os.listdir(BACKUP_DIR), reverse=True):
            full = os.path.join(BACKUP_DIR, d)
            if os.path.isdir(full):
                stat = os.stat(full)
                backups.append({
                    "name": d,
                    "path": full,
                    "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                })
        return backups
    except (FileNotFoundError, PermissionError):
        return []


def rollback(backup_name: str) -> Tuple[bool, str]:
    """
    回滚到指定备份

    参数:
        backup_name: 备份目录名（如 xpm-suite-20250115-143022）

    返回:
        (是否成功, 说明)
    """
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    if not os.path.isdir(backup_path):
        return False, f"备份不存在: {backup_name}"

    try:
        import shutil

        # 恢复 share 目录
        share_backup = f"{backup_path}-share"
        if os.path.isdir(share_backup):
            target = "/usr/local/share/xpm"
            if os.path.isdir(target):
                shutil.rmtree(target)
            shutil.copytree(share_backup, target)

        # 恢复二进制
        for bin_name in ["xpm", "xstore", "xstore-gui"]:
            bin_backup = f"{backup_path}-{bin_name}"
            if os.path.exists(bin_backup):
                target = f"/usr/local/bin/{bin_name}"
                shutil.copy2(bin_backup, target)
                os.chmod(target, 0o755)

        return True, f"已回滚到 {backup_name}"
    except PermissionError:
        return False, "需要 root 权限执行回滚"
    except Exception as e:
        return False, f"回滚失败: {e}"


# ============================================================
# 与 PAM 集成
# ============================================================

def verify_self_update_auth() -> Tuple[bool, str]:
    """
    自更新授权检查（critical 级别）

    需要配合 core.auth 模块使用。
    如果 auth 模块不可用，降级为密码提示。
    """
    try:
        from .auth import verify_action, AuthAction
        return verify_action(AuthAction.SELF_UPGRADE, "XPM Suite")
    except ImportError:
        # 降级：直接要求密码
        print("  🔐 自更新需要授权 (critical)")
        try:
            import getpass
            pwd = getpass.getpass("  root 密码: ")
            import crypt
            import spwd
            entry = spwd.getspnam("root")
            if crypt.crypt(pwd, entry.sp_pwd) == entry.sp_pwd:
                return True, "密码验证通过"
            return False, "密码错误"
        except Exception:
            return False, "无法验证（需要 root）"


# ============================================================
# CLI 输出格式化
# ============================================================

def format_update_status() -> str:
    """返回人类可读的更新状态"""
    info = check_update()
    lines = []
    lines.append(f"  📦 当前版本: v{info['current']}")

    if info["latest"]:
        lines.append(f"  🌐 最新版本: v{info['latest']}")
        if info["update_available"]:
            lines.append(f"  🔔 状态: 🟢 有更新可用!")
            if info.get("release_date"):
                lines.append(f"  📅 发布日期: {info['release_date']}")
            if info["changelog"]:
                lines.append(f"  📝 更新日志:")
                for line in info["changelog"].splitlines()[:10]:
                    line = line.strip()
                    if line:
                        lines.append(f"     {line}")
            if info["size"]:
                size_kb = info["size"] / 1024
                lines.append(f"  📊 大小: {size_kb:.1f} KB")
        else:
            lines.append(f"  ✅ 状态: 已是最新版本")
    else:
        lines.append(f"  ⚠️ 无法检查更新（网络不可用）")

    return "\n".join(lines)


# ============================================================
# 直接运行测试
# ============================================================

if __name__ == "__main__":
    print("=== XPM Self-Update Module Test ===\n")

    print("当前版本:", get_current_version())
    print("代号:", get_current_codename())

    print("\n检查更新:")
    print(format_update_status())

    print("\n备份列表:")
    for b in list_backups():
        print(f"  📁 {b['name']} ({b['date']})")

    print("\n版本比较测试:")
    tests = [("3.0.0", "3.1.0", -1), ("3.0.0", "3.0.0", 0),
             ("3.1.0", "3.0.0", 1), ("2.9.9", "3.0.0", -1)]
    for a, b, expected in tests:
        result = compare_versions(a, b)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {a} vs {b}: {result} (expected {expected})")

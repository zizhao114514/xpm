"""
.deb 包解析模块
纯 Python 实现，零外部依赖
解析 ar 归档 → 提取 control.tar.* + data.tar.* → 解析 control 字段
"""

import io, os, hashlib, time
from typing import Dict, List, Optional, Tuple

from .ar import ar_read_members, ar_extract, verify_deb
from .untar import (
    parse_tar, untar_stream, extract_control_info, parse_control_fields,
    detect_compression, decompress, TarEntry,
)

class DebPackage:
    """解析后的 .deb 包信息"""

    def __init__(self, path: str = "", data: bytes = b""):
        self.path = path
        self._data = data
        self.control: Dict[str, str] = {}
        self.depends: List[str] = []
        self.pre_depends: List[str] = []
        self.provides: List[str] = []
        self.conflicts: List[str] = []
        self.replaces: List[str] = []
        self.breaks: List[str] = []
        self.suggests: List[str] = []
        self.recommends: List[str] = []
        self.triggers: Dict[str, List[str]] = {}
        self.maintainer_scripts: Dict[str, bytes] = {}
        self.data_tar: Optional[bytes] = None
        self.control_tar: Optional[bytes] = None
        self.architecture: str = "all"
        self.name: str = ""
        self.version: str = ""
        self.description: str = ""
        self.size: int = 0  # 解压后大小估算
        self.installed_size: int = 0
        self.priority: str = ""
        self.section: str = ""
        self.source: str = ""
        self.homepage: str = ""
        self._members = []

        if path:
            with open(path, "rb") as f:
                self._data = f.read()
        if self._data:
            self._parse()

    def _parse(self):
        """解析 ar 归档"""
        self._members = ar_read_members(self._data)

        # 提取 control.tar.* 和 data.tar.*
        for m in self._members:
            name = m.name
            if name.startswith("control.tar"):
                self.control_tar = m.data
                self._parse_control_tar(m.data)
            elif name.startswith("data.tar"):
                self.data_tar = m.data
                self._estimate_size(m.data)

        # 提取 maintainer scripts
        self._extract_scripts()

    def _parse_control_tar(self, data: bytes):
        """解析 control.tar.* 中的 control 文件"""
        fmt = detect_compression(data)
        raw = data
        if fmt != "none":
            raw = decompress(data, fmt)

        entries = parse_tar(raw)
        for e in entries:
            if e.name == "control" or e.name.endswith("/control"):
                self.control = parse_control_fields(e.data.decode("utf-8", errors="replace"))
                self._populate_from_control()
                break

        # 也看看有没有 .triggers 文件
        for e in entries:
            if e.name.endswith(".triggers"):
                self._parse_triggers_file(e.data.decode("utf-8", errors="replace"))

    def _populate_from_control(self):
        """从 control 字典填充字段"""
        c = self.control
        self.name = c.get("Package", "")
        self.version = c.get("Version", "")
        self.architecture = c.get("Architecture", "all")
        self.description = c.get("Description", "").split("\n")[0]
        self.priority = c.get("Priority", "")
        self.section = c.get("Section", "")
        self.source = c.get("Source", self.name)
        self.homepage = c.get("Homepage", "")
        try:
            self.installed_size = int(c.get("Installed-Size", "0"))
        except ValueError:
            self.installed_size = 0

        # 解析依赖字段
        self.depends = _split_depends(c.get("Depends", ""))
        self.pre_depends = _split_depends(c.get("Pre-Depends", ""))
        self.provides = [p.strip() for p in c.get("Provides", "").split(",") if p.strip()]
        self.conflicts = [p.strip() for p in c.get("Conflicts", "").split(",") if p.strip()]
        self.replaces = [p.strip() for p in c.get("Replaces", "").split(",") if p.strip()]
        self.breaks = [p.strip() for p in c.get("Breaks", "").split(",") if p.strip()]
        self.suggests = [p.strip() for p in c.get("Suggests", "").split(",") if p.strip()]
        self.recommends = [p.strip() for p in c.get("Recommends", "").split(",") if p.strip()]

        # 触发器字段
        for field in ["Triggers-Pending", "Interest", "Activate"]:
            val = c.get(field, "")
            if val:
                self.triggers[field.lower()] = [t.strip() for t in val.split(",") if t.strip()]

    def _parse_triggers_file(self, text: str):
        """解析 .triggers 文件"""
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, val = line.partition(":")
                self.triggers[key.strip().lower()] = [v.strip() for v in val.split() if v.strip()]

    def _extract_scripts(self):
        """从 control.tar 提取 maintainer scripts"""
        if not self.control_tar:
            return
        fmt = detect_compression(self.control_tar)
        raw = self.control_tar
        if fmt != "none":
            raw = decompress(self.control_tar, fmt)

        entries = parse_tar(raw)
        for e in entries:
            if e.name in ("preinst", "postinst", "prerm", "postrm"):
                self.maintainer_scripts[e.name] = e.data

    def _estimate_size(self, data: bytes):
        """估算解压后大小"""
        fmt = detect_compression(data)
        if fmt != "none":
            try:
                raw = decompress(data, fmt)
            except Exception:
                self.size = len(data) * 3  # 粗估
                return
        else:
            raw = data
        # tar 大小近似 = 文件数 × 平均块
        try:
            entries = parse_tar(raw)
            self.size = sum(e.size for e in entries)
        except Exception:
            self.size = len(raw)

    def verify(self) -> Tuple[bool, str]:
        """校验 .deb 完整性"""
        if not verify_deb(self._data):
            return (False, "不是有效的 .deb (ar magic 错误)")
        if not self.name:
            return (False, "control 文件缺少 Package 字段")
        if not self.version:
            return (False, "control 文件缺少 Version 字段")
        if not self.data_tar:
            return (False, "缺少 data.tar")
        return (True, "OK")

    def get_sha256(self) -> str:
        return hashlib.sha256(self._data).hexdigest()

    def get_md5(self) -> str:
        return hashlib.md5(self._data).hexdigest()

    def list_files(self) -> List[str]:
        """列出包内所有文件路径"""
        if not self.data_tar:
            return []
        fmt = detect_compression(self.data_tar)
        raw = self.data_tar
        if fmt != "none":
            try:
                raw = decompress(self.data_tar, fmt)
            except Exception:
                return []
        entries = parse_tar(raw)
        return [e.name for e in entries if e.is_file or e.is_symlink]

    def extract_data(self, dest: str = ".", progress_cb=None) -> List[str]:
        """解压 data.tar.* 到目标目录"""
        if not self.data_tar:
            return []
        fmt = detect_compression(self.data_tar)
        data = self.data_tar
        if fmt != "none":
            data = decompress(data, fmt)
        return untar_stream(data, dest, progress_cb)

    def extract_control_script(self, script_name: str, dest_path: str) -> bool:
        """提取 maintainer script 到文件"""
        data = self.maintainer_scripts.get(script_name)
        if not data:
            return False
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(data)
        os.chmod(dest_path, 0o755)
        return True

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "arch": self.architecture,
            "source_format": "deb",
            "depends": self.depends,
            "pre_depends": self.pre_depends,
            "provides": self.provides,
            "conflicts": self.conflicts,
            "replaces": self.replaces,
            "breaks": self.breaks,
            "suggests": self.suggests,
            "recommends": self.recommends,
            "triggers": self.triggers,
            "description": self.description,
            "section": self.section,
            "priority": self.priority,
            "installed_size": self.installed_size,
            "homepage": self.homepage,
            "sha256": self.get_sha256(),
        }

    def __repr__(self):
        return f"DebPackage({self.name} {self.version} [{self.architecture}])"

# === 辅助函数 ===

def _split_depends(field: str) -> List[str]:
    """解析 Depends 字段，处理 | 和 (>=version)"""
    if not field.strip():
        return []
    # 先按逗号分（顶层依赖）
    parts = []
    current = ""
    paren = 0
    for ch in field:
        if ch == "(":
            paren += 1
            current += ch
        elif ch == ")":
            paren -= 1
            current += ch
        elif ch == "," and paren == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())

    # 每个 part 可能含 | （或关系）
    results = []
    for p in parts:
        alternatives = [a.strip() for a in p.split("|")]
        results.append(alternatives)
    return results

def parse_deb_file(path: str) -> DebPackage:
    return DebPackage(path=path)

def parse_deb_data(data: bytes) -> DebPackage:
    return DebPackage(data=data)

def verify_deb_file(path: str) -> Tuple[bool, str]:
    """快速校验 .deb 文件"""
    try:
        with open(path, "rb") as f:
            magic = f.read(8)
        if magic != b"!<arch>\n":
            return (False, f"不是 ar 归档，magic={magic!r}")
        return (True, "OK")
    except Exception as e:
        return (False, str(e))

# === 命令行入口 ===

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python -m xpm_suite.formats.deb <file.deb>")
        sys.exit(1)
    pkg = DebPackage(path=sys.argv[1])
    ok, msg = pkg.verify()
    icon = "✅" if ok else "❌"
    print(f"{icon} 校验: {msg}")
    print(f"  包名: {pkg.name}")
    print(f"  版本: {pkg.version}")
    print(f"  架构: {pkg.architecture}")
    print(f"  描述: {pkg.description}")
    print(f"  依赖: {pkg.depends}")
    print(f"  大小: {pkg.size} bytes (解压后估算)")
    print(f"  SHA256: {pkg.get_sha256()[:16]}...")
    print(f"  文件数: {len(pkg.list_files())}")
    if pkg.maintainer_scripts:
        print(f"  脚本: {list(pkg.maintainer_scripts.keys())}")

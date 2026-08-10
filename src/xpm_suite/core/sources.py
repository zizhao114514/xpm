"""
XPM Suite 软件源管理
目录: /etc/xpm/sources.list.d/*.list
支持 Debian 标准语法:
  deb [arch=arm64] https://mirror/debian/ trixie main contrib
  deb https://mirror/debian/ trixie-updates main
"""

import os
import glob
import tempfile
import shutil
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

SOURCES_DIR = "/etc/xpm/sources.list.d"


# === 数据结构 ===

@dataclass
class SourceEntry:
    """单条软件源记录"""
    url: str                    # https://mirrors.tuna.tsinghua.edu.cn/debian/
    suite: str                  # trixie
    components: List[str]       # ["main", "contrib"]
    arch: Optional[str] = None  # arm64 / amd64 / None=all arch
    options: dict = field(default_factory=dict)
    enabled: bool = True
    file: str = ""              # 所属文件名
    line_number: int = 0
    raw: str = ""               # 原始行

    def to_line(self) -> str:
        """序列化为源文件行"""
        opts = ""
        if self.arch:
            opts = f"[arch={self.arch}] "
        comps = " ".join(self.components)
        return f"deb {opts}{self.url} {self.suite} {comps}"

    def __str__(self):
        return self.to_line()


# === 解析 ===

def parse_source_line(line: str) -> Optional[SourceEntry]:
    """
    解析一行 deb 源配置。
    支持:
      deb [arch=arm64 lang=en_US] https://mirror suite comp1 comp2
      deb https://mirror suite comp1 arch=arm64
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    parts = stripped.split()
    if not parts or parts[0] not in ("deb", "deb-src"):
        return None

    is_src = (parts[0] == "deb-src")
    idx = 1

    # 解析 [key=value key=value] 选项块
    options = {}
    if parts[idx].startswith("[") and not parts[idx].startswith("http"):
        opt_str = ""
        while idx < len(parts) and "]" not in parts[idx]:
            opt_str += parts[idx] + " "
            idx += 1
        if idx < len(parts):
            opt_str += parts[idx]
            idx += 1
        opt_str = opt_str.strip("[]").strip()
        for kv in opt_str.split():
            if "=" in kv:
                k, v = kv.split("=", 1)
                options[k.strip()] = v.strip()

    # url
    if idx >= len(parts):
        return None
    url = parts[idx]
    idx += 1

    # suite
    if idx >= len(parts):
        return None
    suite = parts[idx]
    idx += 1

    # components + 尾部 arch=
    comps = []
    arch = options.get("arch")
    while idx < len(parts):
        c = parts[idx]
        if c.startswith("arch="):
            arch = c.split("=", 1)[1]
        else:
            comps.append(c)
        idx += 1

    return SourceEntry(
        url=url.rstrip("/"),
        suite=suite,
        components=comps,
        arch=arch,
        options=options,
        enabled=True,
        raw=stripped,
    )


def parse_sources_file(filepath: str) -> List[SourceEntry]:
    """解析单个 .list 文件"""
    entries = []
    if not os.path.exists(filepath):
        return entries
    with open(filepath) as f:
        for i, line in enumerate(f, 1):
            entry = parse_source_line(line)
            if entry is not None:
                entry.file = os.path.basename(filepath)
                entry.line_number = i
                entries.append(entry)
    return entries


def load_all_sources() -> List[SourceEntry]:
    """扫描 /etc/xpm/sources.list.d/*.list 返回所有源"""
    entries = []
    pattern = os.path.join(SOURCES_DIR, "*.list")
    for fpath in sorted(glob.glob(pattern)):
        try:
            entries.extend(parse_sources_file(fpath))
        except (PermissionError, OSError):
            pass
    return entries


# === 写入 ===

def write_sources_file(filepath: str, entries: List[SourceEntry],
                       header: str = ""):
    """原子写入源文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tmp = filepath + ".tmp"
    with open(tmp, "w") as f:
        if header:
            f.write(header)
        for e in entries:
            f.write(e.to_line() + "\n")
    os.replace(tmp, filepath)


def add_source(entry: SourceEntry, filename: str = "custom.list"):
    """添加一条源到指定文件"""
    if not filename.endswith(".list"):
        filename += ".list"
    # 安全检查
    if "/" in filename or ".." in filename:
        raise ValueError("文件名不能包含路径分隔符")
    fpath = os.path.join(SOURCES_DIR, filename)
    existing = parse_sources_file(fpath)
    existing.append(entry)
    write_sources_file(fpath, existing,
                       header=f"# XPM Suite 软件源 - {filename}\n")
    return fpath


def remove_source(filename: str, line_number: int):
    """删除指定文件的某一行"""
    if not filename.endswith(".list"):
        filename += ".list"
    fpath = os.path.join(SOURCES_DIR, filename)
    entries = parse_sources_file(fpath)
    remaining = [e for e in entries if e.line_number != line_number]
    write_sources_file(fpath, remaining)


# === 架构推断 ===

def get_arch_for_source(entry: SourceEntry, fallback: str) -> str:
    """获取该源应使用的架构"""
    return entry.arch or fallback


# === 迁移旧配置 ===

def migrate_legacy_sources_list():
    """
    如果旧版 /etc/xpm/sources.list (单文件) 存在，
    迁移到 /etc/xpm/sources.list.d/legacy.list
    """
    legacy = "/etc/xpm/sources.list"
    if not os.path.exists(legacy):
        return 0

    target_dir = SOURCES_DIR
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, "legacy.list")

    count = 0
    with open(legacy) as fin, open(target, "w") as fout:
        fout.write("# 从 /etc/xpm/sources.list 自动迁移\n")
        for line in fin:
            entry = parse_source_line(line)
            if entry is not None:
                fout.write(entry.to_line() + "\n")
                count += 1

    # 备份旧文件
    shutil.move(legacy, legacy + ".migrated")
    return count


# === 诊断 ===

def validate_sources() -> List[Tuple[str, str]]:
    """验证所有源，返回 (级别, 消息) 列表"""
    issues = []
    entries = load_all_sources()

    if not entries:
        issues.append(("warn", f"没有找到任何软件源，请检查 {SOURCES_DIR}/"))
        return issues

    seen = set()
    for e in entries:
        # 检查重复
        key = (e.url, e.suite, tuple(e.components))
        if key in seen:
            issues.append(("warn", f"重复源: {e.to_line()}"))
        seen.add(key)

        # 检查 URL 格式
        if not e.url.startswith(("http://", "https://", "mirror://")):
            issues.append(("error", f"无效 URL: {e.url}"))

        # 检查 components
        if not e.components:
            issues.append(("warn", f"源没有指定 component: {e.url} {e.suite}"))

    return issues


if __name__ == "__main__":
    # 简单测试
    test = 'deb [arch=arm64] https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main contrib non-free'
    e = parse_source_line(test)
    print(f"解析结果: {e}")
    print(f"序列化:   {e.to_line()}")

    print("\n=== 当前源 ===")
    for e in load_all_sources():
        print(f"  {e}")

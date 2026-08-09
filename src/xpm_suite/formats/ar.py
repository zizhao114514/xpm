"""
纯 Python ar 归档解析（BSD/GNU 两种格式兼容）
用于解析 .deb 包（ar 归档 → control.tar + data.tar）
零外部依赖
"""

import struct, io, zlib
from typing import Dict, Optional

AR_MAGIC = b"!<arch>\n"
AR_MAGIC_LEGACY = b"!<arch>\n"  # BSD/GNU 标准

# GNU 扩展：长文件名表
GNU_TABLE_NAME = b"//"
GNU_LONGFILE_NAME = b"/"

class ArMember:
    __slots__ = ("name", "mtime", "uid", "gid", "mode", "size", "data", "offset")
    def __init__(self, name, mtime, uid, gid, mode, size, data, offset=0):
        self.name = name
        self.mtime = mtime
        self.uid = uid
        self.gid = gid
        self.mode = mode
        self.size = size
        self.data = data
        self.offset = offset

    def __repr__(self):
        return f"ArMember(name={self.name!r}, size={self.size}, mode={self.mode:o})"

def _pad(size, align=2):
    """ar 使用 2 字节对齐"""
    return (size + align - 1) // align * align

def _read_field(buf, pos, length):
    """读取定长字段并 strip（空格和 null 字节）"""
    return buf[pos:pos+length].decode("ascii", errors="replace").strip(" \x00")

def ar_read_members(data: bytes) -> list[ArMember]:
    """
    解析 ar 归档，返回成员列表。
    支持 BSD ar 和 GNU ar（长文件名表）。
    """
    if len(data) < 8:
        raise ValueError("文件太小，不是有效的 ar 归档")

    # 检查 magic
    if data[:8] != AR_MAGIC:
        # 有些文件 magic 略有不同，尝试兼容
        if b"!<arch>" not in data[:16]:
            raise ValueError(f"不是有效的 ar 归档，magic={data[:8]!r}")
        # 跳过非标准前缀（极少数情况）
        # 标准 ar 必须以 !<arch>\n 开头

    pos = 8
    members = []
    long_names = {}  # GNU 长文件名表

    while pos < len(data):
        if pos + 60 > len(data):
            break

        # 解析 header（60 字节定长）
        name = _read_field(data, pos, 16)
        mtime = int(_read_field(data, pos+16, 12) or "0")
        uid   = int(_read_field(data, pos+28, 6) or "0")
        gid   = int(_read_field(data, pos+34, 6) or "0")
        mode  = int(_read_field(data, pos+40, 8) or "0", 8)
        size  = int(_read_field(data, pos+48, 10) or "0")
        fmag  = data[pos+58:pos+60]

        # 验证文件头标记
        if fmag != b"\x60\n":
            # 尝试跳过对齐填充
            if data[pos:pos+2] == b"\x60\n":
                pos += 2
                continue
            raise ValueError(f"ar header 标记错误 @ {pos}: {fmag!r}")

        pos += 60

        # 读取数据
        if pos + size > len(data):
            raise ValueError(f"ar 成员 {name!r} 数据超出文件范围")
        content = data[pos:pos+size]
        pos += _pad(size)

        # 处理 GNU 长文件名
        if name == GNU_TABLE_NAME.decode():
            # 长文件名表：以 / 分隔
            names_list = content.rstrip(b"\x00").split(b"/")
            for i, n in enumerate(names_list):
                if n:
                    long_names[i] = n.decode("utf-8", errors="replace")
            continue

        actual_name = name
        if name.startswith(GNU_LONGFILE_NAME.decode()):
            # /N → 长文件名表中的第 N 个
            try:
                idx = int(name[1:])
                actual_name = long_names.get(idx, name)
            except ValueError:
                actual_name = name
        else:
            # BSD 风格：末尾可能有 /
            actual_name = name.rstrip("/")

        members.append(ArMember(
            name=actual_name, mtime=mtime, uid=uid, gid=gid,
            mode=mode, size=size, data=content, offset=pos-size
        ))

    return members

def ar_extract(data: bytes, member_name: str) -> Optional[bytes]:
    """提取指定成员的内容"""
    members = ar_read_members(data)
    for m in members:
        if m.name == member_name:
            return m.data
        # 也尝试匹配常见变体
        if member_name == "control.tar.gz" and m.name.startswith("control.tar"):
            return m.data
        if member_name == "data.tar.gz" and m.name.startswith("data.tar"):
            return m.data
    return None

def verify_deb(data: bytes) -> bool:
    """快速校验是否为有效 .deb（ar 归档 + 必要成员）"""
    try:
        members = ar_read_members(data)
        names = {m.name for m in members}
        # .deb 至少需要 control.tar 和 data.tar
        has_control = any(n.startswith("control.tar") for n in names)
        has_data = any(n.startswith("data.tar") for n in names)
        return has_control and has_data
    except Exception:
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python -m xpm_suite.formats.ar <file.deb>")
        sys.exit(1)
    with open(sys.argv[1], "rb") as f:
        data = f.read()
    if not verify_deb(data):
        print("❌ 不是有效的 .deb 文件")
        sys.exit(1)
    members = ar_read_members(data)
    print(f"✅ 有效 .deb，{len(members)} 个成员:")
    for m in members:
        print(f"  {m.name:<30} {m.size:>10} bytes  mode={m.mode:o}")

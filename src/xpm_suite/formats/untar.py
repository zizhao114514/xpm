"""
纯 Python tar 解压（支持 gz / xz / bz2 / zstd / 不压缩）
用于解包 .deb 的 data.tar.* 和 control.tar.*
零外部依赖（标准库 zlib/bz2/lzma；zstd 可选）
"""

import io, struct, os, stat, pwd, grp
from typing import Dict, Optional, BinaryIO

# === 压缩格式自动检测 ===

def detect_compression(data: bytes) -> str:
    """检测数据压缩格式"""
    # zstd: 28 b5 2f fd (4 bytes, check first since it's shortest)
    if len(data) >= 4 and data[:4] == bytes([0x28, 0xb5, 0x2f, 0xfd]):
        return "zstd"
    if len(data) < 6:
        return "none"
    # gzip: 1f 8b
    if data[:2] == b"\x1f\x8b":
        return "gzip"
    # bzip2: BZh
    if data[:3] == b"BZh":
        return "bzip2"
    # xz: fd 37 7a 58 5a 00
    if data[:6] == b"\xfd\x37\x7a\x58\x5a\x00":
        return "xz"
    return "none"

def decompress(data: bytes, fmt: str = "auto") -> bytes:
    """解压数据"""
    if fmt == "auto":
        fmt = detect_compression(data)
    if fmt == "gzip":
        import gzip
        return gzip.decompress(data)
    elif fmt == "bzip2":
        import bz2
        return bz2.decompress(data)
    elif fmt == "xz":
        import lzma
        return lzma.decompress(data)
    elif fmt == "zstd":
        try:
            import zstandard as zstd
            return zstd.decompress(data)
        except ImportError:
            # 回退：用 subprocess
            import subprocess, tempfile
            with tempfile.NamedTemporaryFile(suffix=".zst", mode="wb", delete=False) as f:
                f.write(data)
                p = f.name
            subprocess.run(["zstd", "-d", "-f", "-o", p + ".out", p], check=True)
            with open(p + ".out", "rb") as f:
                return f.read()
    return data

# === tar 解析 ===

TAR_BLOCK = 512

def _read_octal(buf, offset, length):
    """解析 tar 的八进制字段"""
    s = buf[offset:offset+length].decode("ascii", errors="replace").strip()
    s = s.replace("\x00", "").strip()
    if not s:
        return 0
    # 可能以空格结尾
    try:
        return int(s, 8)
    except ValueError:
        # 有些 tar 用 base-256
        if buf[offset] & 0x80:
            n = 0
            for i in range(length):
                n = (n << 8) | buf[offset+i]
            return n & ~(1 << (length * 8 - 1))
        return 0

class TarEntry:
    __slots__ = ("name", "size", "mode", "uid", "gid", "mtime", "type", "linkname", "data")
    def __init__(self, name, size, mode, uid, gid, mtime, type_, linkname, data):
        self.name = name
        self.size = size
        self.mode = mode
        self.uid = uid
        self.gid = gid
        self.mtime = mtime
        self.type = type_
        self.linkname = linkname
        self.data = data

    @property
    def is_dir(self):
        return self.type == b"5" or self.name.endswith("/")

    @property
    def is_file(self):
        return self.type == b"0" or self.type == b""

    @property
    def is_symlink(self):
        return self.type == b"2"

def parse_tar(data: bytes) -> list[TarEntry]:
    """解析 tar 归档（ustar 格式）"""
    entries = []
    pos = 0
    while pos + TAR_BLOCK <= len(data):
        header = data[pos:pos+TAR_BLOCK]

        # 检查结束标记（512 字节全零）
        if header == b"\x00" * TAR_BLOCK:
            # 跳过后续的零块（GNU tar 用两个零块结尾）
            pos += TAR_BLOCK
            continue

        # 解析 header
        name = header[0:100].rstrip(b"\x00").decode("utf-8", errors="replace")
        mode = _read_octal(header, 100, 8)
        uid  = _read_octal(header, 108, 8)
        gid  = _read_octal(header, 116, 8)
        size = _read_octal(header, 124, 12)
        mtime = _read_octal(header, 136, 12)
        chksum = _read_octal(header, 148, 8)
        type_ = header[156:157]
        linkname = header[157:257].rstrip(b"\x00").decode("utf-8", errors="replace")

        # ustar 扩展头（100-255 偏移）
        ustar_magic = header[257:263]
        if ustar_magic.startswith(b"ustar"):
            # 长文件名可能在 prefix
            prefix = header[345:500].rstrip(b"\x00").decode("utf-8", errors="replace")
            if prefix and not name.startswith("/"):
                name = prefix + "/" + name

        pos += TAR_BLOCK

        # 读取文件数据
        data_blocks = (size + TAR_BLOCK - 1) // TAR_BLOCK
        file_data = data[pos:pos + data_blocks * TAR_BLOCK][:size]
        pos += data_blocks * TAR_BLOCK

        # 跳过 GNU long linkname / long name 扩展
        if type_ == b"L":  # GNU long name
            name = file_data.rstrip(b"\x00").decode("utf-8", errors="replace")
            continue  # 下一条 entry 会用到这个名字
        if type_ == b"K":  # GNU long linkname
            linkname = file_data.rstrip(b"\x00").decode("utf-8", errors="replace")
            continue

        entries.append(TarEntry(name, size, mode, uid, gid, mtime, type_, linkname, file_data))

    return entries

def untar_stream(data: bytes, dest: str = ".", progress_cb=None):
    """
    解压 tar 数据到目标目录。
    支持 gz/xz/bz2/zstd/不压缩 自动检测。
    """
    # 先解压
    fmt = detect_compression(data)
    if fmt != "none":
        data = decompress(data, fmt)

    entries = parse_tar(data)
    installed = []

    for i, e in enumerate(entries):
        target = os.path.join(dest, e.name.lstrip("/"))

        if progress_cb:
            progress_cb(i, len(entries), e.name)

        if e.is_dir:
            os.makedirs(target, exist_ok=True)
        elif e.is_symlink:
            os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
            if os.path.exists(target) or os.path.islink(target):
                os.remove(target)
            os.symlink(e.linkname, target)
            installed.append(e.name)
        elif e.is_file:
            os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
            with open(target, "wb") as f:
                f.write(e.data)
            # 设置权限
            try:
                os.chmod(target, e.mode & 0o7777)
            except OSError:
                pass
            installed.append(e.name)

    return installed

def extract_control_info(data: bytes) -> Dict[str, str]:
    """
    从 control.tar.* 中提取 control 信息。
    返回 {field: value} 字典。
    """
    fmt = detect_compression(data)
    if fmt != "none":
        data = decompress(data, fmt)

    entries = parse_tar(data)
    for e in entries:
        if e.name == "control" or e.name.endswith("/control"):
            return parse_control_fields(e.data.decode("utf-8", errors="replace"))

    # 也可能 control 在 ./control
    for e in entries:
        if "control" in e.name:
            return parse_control_fields(e.data.decode("utf-8", errors="replace"))

    return {}

def parse_control_fields(control_text: str) -> Dict[str, str]:
    """解析 Debian control 文件字段"""
    fields = {}
    current_key = None
    for line in control_text.splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current_key:
            # 续行
            fields[current_key] += "\n " + line.strip()
        elif ":" in line:
            key, _, value = line.partition(":")
            current_key = key.strip()
            fields[current_key] = value.strip()
    return fields

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python -m xpm_suite.formats.untar <file.tar.*>")
        sys.exit(1)
    with open(sys.argv[1], "rb") as f:
        data = f.read()
    fmt = detect_compression(data)
    print(f"压缩格式: {fmt}")
    if fmt != "none":
        data = decompress(data, fmt)
    entries = parse_tar(data)
    print(f"共 {len(entries)} 个条目:")
    for e in entries[:20]:
        t = "📁" if e.is_dir else "🔗" if e.is_symlink else "📄"
        print(f"  {t} {e.name:<50} {e.size:>10}  mode={e.mode:o}")

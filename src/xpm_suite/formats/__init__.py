"""
XPM Suite 包格式引擎
支持 .deb (ar+tar) 和 .oil (tar.gz+manifest)
"""

from .ar import (
    ar_read_members, ar_extract, verify_deb, ArMember,
    AR_MAGIC,
)
from .untar import (
    parse_tar, untar_stream, extract_control_info, parse_control_fields,
    detect_compression, decompress, TarEntry,
)

__all__ = [
    "ar_read_members", "ar_extract", "verify_deb", "ArMember", "AR_MAGIC",
    "parse_tar", "untar_stream", "extract_control_info", "parse_control_fields",
    "detect_compression", "decompress", "TarEntry",
]

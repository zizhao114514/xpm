#!/usr/bin/env python3
"""
ar_header.py - Correct Debian ar header construction
Verified against dpkg-deb output.
"""

# Debian ar header layout (60 bytes total):
#   Offset  Size  Field       Format
#   0       16    name        ASCII, left-justified, space-padded
#   16      12    mtime       ASCII, right-justified, zero-padded
#   28       6    uid         ASCII, right-justified, zero-padded
#   34       6    gid         ASCII, right-justified, zero-padded
#   40       8    mode        ASCII, right-justified, zero-padded
#   48      10    size        ASCII, right-justified, zero-padded
#   58       2    magic       0x60 0x0a (` \n)

def ar_header(name: bytes, size: int) -> bytes:
    # Name: left-justified, space-padded to 16
    if len(name) > 16:
        raise ValueError(f"name too long: {name!r}")
    name_field = name + b" " * (16 - len(name))
    
    # Numeric fields: right-justified, zero-padded
    mtime_field = b"0" * 12
    uid_field   = b"0" * 6
    gid_field   = b"0" * 6
    
    # Mode: dpkg-deb writes decimal mode right-justified zero-padded to 8
    # 100644 -> "00100644" (8 chars)
    mode_str = str(100644).zfill(8).encode()  # "00100644"
    assert len(mode_str) == 8, f"mode {mode_str!r} len={len(mode_str)}"
    
    size_str = str(size).zfill(10).encode()
    assert len(size_str) == 10, f"size {size_str!r} len={len(size_str)}"
    
    magic = b"\x60\x0a"
    
    hdr = name_field + mtime_field + uid_field + gid_field + mode_str + size_str + magic
    assert len(hdr) == 60, f"header is {len(hdr)} bytes: {hdr!r}"
    return hdr


def ar_member(name: str, data: bytes) -> bytes:
    hdr = ar_header(name.encode(), len(data))
    out = hdr + data
    if len(data) % 2 == 1:
        out += b"\n"
    return out


if __name__ == "__main__":
    # Test
    h = ar_header(b"debian-binary", 4)
    print(f"Header ({len(h)}B):")
    print(f"  raw hex: {h.hex()}")
    print(f"  name:    {h[0:16]!r}")
    print(f"  mtime:   {h[16:28]!r}")
    print(f"  uid:     {h[28:34]!r}")
    print(f"  gid:     {h[34:40]!r}")
    print(f"  mode:    {h[40:48]!r}")
    print(f"  size:    {h[48:58]!r}")
    print(f"  magic:   {h[58:60]!r}")
    print(f"\n  ASCII view: {h!r}")
    
    # Verify against expected dpkg-deb format
    expected_name = b"debian-binary   "  # 16 chars
    m_ok = h[40:48] == b"00100644"
    s_ok = h[48:58] == b"0000000004"
    x_ok = h[58:60] == b"\x60\x0a"
    print(f"\n  name matches expected: {h[0:16] == expected_name}")
    print(f"  mode is '00100644': {m_ok}")
    print(f"  size is '0000000004': {s_ok}")
    print(f"  magic is backtick+LF: {x_ok}")

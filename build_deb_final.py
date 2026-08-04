#!/usr/bin/env python3
"""
build_deb_final.py - XPM .deb builder (correct ar format)
Produces a .deb that dpkg-deb -I / -c / apt install all accept.
"""

import os, io, hashlib
from pathlib import Path

VERSION = "2.0-2"
PACKAGE = "xpm"
ARCH = "all"
STAGING = Path("staging")
DIST = Path("dist")
DIST.mkdir(exist_ok=True)

# ─── ar header ────────────────────────────────────────────────────────────

def ar_header(name: bytes, size: int) -> bytes:
    """Debian ar header: 60 bytes."""
    assert len(name) <= 16, f"name too long: {name!r}"
    name_field  = name + b" " * (16 - len(name))
    mtime_field = b"0" * 12
    uid_field   = b"0" * 6
    gid_field   = b"0" * 6
    mode_str    = str(100644).zfill(8).encode()  # "00100644"
    assert len(mode_str) == 8
    size_str    = str(size).zfill(10).encode()
    assert len(size_str) == 10
    magic       = b"\x60\x0a"
    hdr = name_field + mtime_field + uid_field + gid_field + mode_str + size_str + magic
    assert len(hdr) == 60, f"hdr={len(hdr)}"
    return hdr

def ar_member(name: str, data: bytes) -> bytes:
    out = ar_header(name.encode(), len(data)) + data
    if len(data) % 2 == 1:
        out += b"\n"
    return out

# ─── control.tar.gz ───────────────────────────────────────────────────────

def make_control_tar_gz() -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w") as tar:
            control_text = (
                f"Package: {PACKAGE}\n"
                f"Version: {VERSION}\n"
                f"Section: utils\n"
                f"Priority: optional\n"
                f"Architecture: {ARCH}\n"
                f"Maintainer: Zizhao <zizhao@localhost>\n"
                f"Depends: python3, wget\n"
                f"Recommends: curl\n"
                f"Description: X11 Package Manager - Petroleum Edition\n"
                f" A Debian package manager written in Python that uses\n"
                f" wget + dpkg only. Zero apt-get calls. Features dependency\n"
                f" resolution, rollback, GPG, GUI, and oil-powered progress.\n"
            ).encode()
            ti = tarfile.TarInfo(name="control")
            ti.size = len(control_text)
            ti.mtime = 0
            ti.mode = 0o644
            tar.addfile(ti, io.BytesIO(control_text))

            md5 = hashlib.md5(control_text).hexdigest().encode() + b"  control\n"
            ti2 = tarfile.TarInfo(name="md5sums")
            ti2.size = len(md5)
            ti2.mtime = 0
            ti2.mode = 0o644
            tar.addfile(ti2, io.BytesIO(md5))
    return buf.getvalue()

# ─── data.tar.gz ──────────────────────────────────────────────────────────

def add_file(tar, rel_path: str, mode=0o755):
    src = STAGING / rel_path
    if not src.exists():
        print(f"  WARNING: missing {rel_path}")
        return
    data = src.read_bytes()
    ti = tarfile.TarInfo(name=rel_path)
    ti.size = len(data)
    ti.mtime = 0
    ti.mode = mode
    ti.uid = 0
    ti.gid = 0
    tar.addfile(ti, io.BytesIO(data))

def make_data_tar_gz() -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w") as tar:
            add_file(tar, "usr/local/bin/xpm", 0o755)
            add_file(tar, "usr/local/bin/xm", 0o755)
            for d in [
                "usr/local/share/xpm/docs/README.md",
                "usr/local/share/xpm/docs/RELEASE.md",
                "usr/local/share/xpm/docs/FAQ.md",
                "usr/local/share/xpm/docs/design.md",
                "usr/local/share/xpm/docs/manual.md",
                "usr/local/share/xpm/docs/packaging.md",
                "usr/local/share/xpm/docs/internals.md",
            ]:
                add_file(tar, d, 0o644)
            add_file(tar, "usr/local/share/xpm/tests/test_all.py", 0o644)
            add_file(tar, "usr/share/applications/xpm.desktop", 0o644)
    return buf.getvalue()

# ─── Build ────────────────────────────────────────────────────────────────

import gzip, tarfile

def main():
    print("=== XPM .deb Builder (final) ===\n")

    print("[1/5] Reading staged files ...")
    control_gz = make_control_tar_gz()
    data_gz = make_data_tar_gz()
    debian_binary = b"2.0\n"
    print(f"  debian-binary: {len(debian_binary)}B")
    print(f"  control.tar.gz: {len(control_gz)}B")
    print(f"  data.tar.gz: {len(data_gz)}B")

    print("\n[2/5] Verifying gzip streams ...")
    for name, blob in [("control.tar.gz", control_gz), ("data.tar.gz", data_gz)]:
        decompressed = gzip.decompress(blob)
        print(f"  {name}: OK ({len(decompressed)}B)")
        tf = tarfile.open(fileobj=io.BytesIO(decompressed), mode="r:")
        members = [m.name for m in tf.getmembers()]
        print(f"    tar: {members}")
        tf.close()

    print("\n[3/5] Assembling .deb ...")
    out = b"!<arch>\n"
    out += ar_member("debian-binary", debian_binary)
    out += ar_member("control.tar.gz", control_gz)
    out += ar_member("data.tar.gz", data_gz)

    deb_path = DIST / f"{PACKAGE}_{VERSION}_{ARCH}.deb"
    deb_path.write_bytes(out)
    print(f"  Written: {deb_path} ({len(out)}B)")

    print("\n[4/5] dpkg-deb -I (control info) ...")
    rc = os.system(f"dpkg-deb -I {deb_path}")
    print(f"  exit: {rc}")

    print(f"\n[5/5] dpkg-deb -c (file list) ...")
    rc = os.system(f"dpkg-deb -c {deb_path}")
    print(f"  exit: {rc}")

    print(f"\nDone: {deb_path}")

if __name__ == "__main__":
    main()

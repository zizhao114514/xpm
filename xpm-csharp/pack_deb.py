#!/usr/bin/env python3
"""
pack_deb.py - Build xmcs .deb package using Python's arfile module.
Bypasses dpkg-deb which chokes on virtiofs 777 perms.
"""
import os, time, tarfile, io, struct, hashlib

VER = "1.9-0+csharp"
PKG = f"xmcs_{VER}_all"
BUILD = "/data/workspace/xpm-csharp/build"
SRC = "/data/workspace/xpm-csharp"

# Clean
import shutil
shutil.rmtree(f"{BUILD}", ignore_errors=True)
os.makedirs(f"{BUILD}/{PKG}/DEBIAN", exist_ok=True)
os.makedirs(f"{BUILD}/{PKG}/usr/local/share/xmcs/src", exist_ok=True)
os.makedirs(f"{BUILD}/{PKG}/usr/share/doc/xmcs", exist_ok=True)

PKGDIR = f"{BUILD}/{PKG}"

# Copy DEBIAN files
for f in ["control", "postinst", "prerm", "postrm"]:
    shutil.copy(f"{SRC}/DEBIAN/{f}", f"{PKGDIR}/DEBIAN/{f}")

# Copy sources
for f in os.listdir(f"{SRC}/src"):
    if f.endswith(".cs"):
        shutil.copy(f"{SRC}/src/{f}", f"{PKGDIR}/usr/local/share/xmcs/src/{f}")

shutil.copy(f"{SRC}/build.sh",   f"{PKGDIR}/usr/local/share/xmcs/build.sh")
shutil.copy(f"{SRC}/README.md",  f"{PKGDIR}/usr/share/doc/xmcs/README.md")
shutil.copy(f"{SRC}/RELEASE.md", f"{PKGDIR}/usr/share/doc/xmcs/RELEASE.md")

# Generate md5sums
os.chdir(PKGDIR)
md5s = []
for root, dirs, files in os.walk("usr"):
    for fn in sorted(files):
        fp = os.path.join(root, fn)
        h = hashlib.md5(open(fp, "rb").read()).hexdigest()
        md5s.append(f"{h}  {fp}")
with open("DEBIAN/md5sums", "w") as f:
    f.write("\n".join(md5s) + "\n")

# --- Build tar.gz files ---
os.chdir(BUILD)

# control.tar.gz
with tarfile.open("control.tar.gz", "w:gz") as tar:
    tar.add(f"{PKGDIR}/DEBIAN", arcname="DEBIAN")

# data.tar.gz
with tarfile.open("data.tar.gz", "w:gz") as tar:
    tar.add(f"{PKGDIR}/usr", arcname="usr")

# debian-binary
with open("debian-binary", "wb") as f:
    f.write(b"2.0\n")

# --- Combine into .deb using ar format ---
# ar global header: "!<arch>\n"
# Each entry: header (60 bytes) + data + optional padding
def ar_header(name: bytes, size: int, mtime: int) -> bytes:
    """Build a 60-byte ar header."""
    # name: 16 bytes, / terminated for long names
    nm = name[:16]
    if len(nm) < 16:
        nm = nm + b" " * (16 - len(nm))
    # mtime: 12 bytes
    mt = f"{mtime:12d}".encode()
    # uid: 6 bytes
    uid = b"     0"
    # gid: 6 bytes
    gid = b"     0"
    # mode: 8 bytes (octal string)
    mode = b"100644  "
    # size: 10 bytes
    sz = f"{size:10d}".encode()
    # magic: 2 bytes
    magic = b"`\n"
    return nm + mt + uid + gid + mode + sz + magic

def write_ar_entry(out, name: str, data: bytes, mtime: int):
    out.write(ar_header(name.encode(), len(data), mtime))
    out.write(data)
    # 2-byte alignment for odd sizes
    if len(data) % 2 != 0:
        out.write(b"\n")

# Read inputs
debian_binary = open("debian-binary", "rb").read()
control_tgz   = open("control.tar.gz", "rb").read()
data_tgz      = open("data.tar.gz", "rb").read()

mtime = int(time.time())

out_path = "/data/workspace/xpm-csharp/xmcs_1.9-0+csharp_all.deb"
with open(out_path, "wb") as out:
    out.write(b"!<arch>\n")
    write_ar_entry(out, "debian-binary",  debian_binary, mtime)
    write_ar_entry(out, "control.tar.gz", control_tgz,   mtime)
    write_ar_entry(out, "data.tar.gz",    data_tgz,      mtime)

sz = os.path.getsize(out_path)
print(f"✅ Built: {out_path} ({sz} bytes)")

# Verify with ar command if available
import subprocess
r = subprocess.run(["ar", "t", out_path], capture_output=True, text=True)
print("ar contents:")
print(r.stdout.strip())

print()
print("☕ Oil reserve: 100001%")
print("🛢️ Power: 1.x W")

"""
.oil 包格式 - XPM Suite 原生包格式
tar.gz + oil-manifest.json，无 ar 层，更简洁高效

格式规范 v1.0:
  oil-package.tar.gz
  ├── oil-manifest.json    (必须，第一个文件)
  ├── data/                 (包文件，保持目录结构)
  ├── scripts/
  │   ├── preinst
  │   ├── postinst
  │   ├── prerm
  │   └── postrm
  └── triggers             (可选)

oil-manifest.json 字段:
  name, version, arch, format, depends, provides,
  conflicts, replaces, scripts, triggers, files, checksums
"""

import io, os, json, hashlib, tarfile, time
from typing import Dict, List, Optional, Tuple
from pathlib import Path

OIL_FORMAT_VERSION = "1.0"

class OilPackage:
    """解析后的 .oil 包"""

    def __init__(self, path: str = "", data: bytes = b""):
        self.path = path
        self._data = data
        self.manifest: Dict = {}
        self.name: str = ""
        self.version: str = ""
        self.arch: str = "all"
        self.depends: List[List[str]] = []
        self.provides: List[str] = []
        self.conflicts: List[str] = []
        self.replaces: List[str] = []
        self.breaks: List[str] = []
        self.suggests: List[str] = []
        self.recommends: List[str] = []
        self.triggers: Dict[str, List[str]] = {}
        self.maintainer_scripts: Dict[str, bytes] = {}
        self.files: List[str] = []
        self.checksums: Dict[str, str] = {}
        self.description: str = ""
        self.section: str = ""
        self.priority: str = ""
        self.homepage: str = ""
        self.installed_size: int = 0
        self._tar_data: Optional[bytes] = None

        if path:
            with open(path, "rb") as f:
                self._data = f.read()
        if self._data:
            self._parse()

    def _parse(self):
        """解析 .oil 包（tar.gz → manifest + files）"""
        try:
            tar_bytes = self._decompress(self._data)
        except Exception as e:
            raise ValueError(f".oil 解压失败: {e}")

        self._tar_data = tar_bytes
        files_dict = {}

        # 解析 tar
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as tf:
            for m in tf.getmembers():
                if m.isfile():
                    f = tf.extractfile(m)
                    if f:
                        files_dict[m.name] = f.read()

        # 解析 manifest（必须是第一个文件）
        manifest_data = None
        for name, data in files_dict.items():
            if name == "oil-manifest.json" or name.endswith("/oil-manifest.json"):
                manifest_data = data
                break

        if not manifest_data:
            raise ValueError(".oil 包缺少 oil-manifest.json")

        try:
            self.manifest = json.loads(manifest_data.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"oil-manifest.json 解析失败: {e}")

        self._populate_from_manifest()

        # 提取 scripts
        for s in ["preinst", "postinst", "prerm", "postrm"]:
            key = f"scripts/{s}"
            for name, data in files_dict.items():
                if name == key or name.endswith("/" + key):
                    self.maintainer_scripts[s] = data
                    break

    def _decompress(self, data: bytes) -> bytes:
        """自动检测并解压"""
        if data[:2] == b"\x1f\x8b":
            import gzip
            return gzip.decompress(data)
        elif data[:3] == b"BZh":
            import bz2
            return bz2.decompress(data)
        elif data[:6] == b"\xfd\x37\x7a\x58\x5a\x00":
            import lzma
            return lzma.decompress(data)
        # 可能是未压缩的 tar
        if data[:5] == b"ustar" or data[:6] == b"ustar ":
            return data
        raise ValueError("无法识别的压缩格式")

    def _populate_from_manifest(self):
        m = self.manifest
        self.name = m.get("name", "")
        self.version = m.get("version", "")
        self.arch = m.get("arch", "all")
        self.description = m.get("description", "")
        self.section = m.get("section", "")
        self.priority = m.get("priority", "")
        self.homepage = m.get("homepage", "")
        self.installed_size = m.get("installed_size", 0)

        # 依赖
        self.depends = m.get("depends", [])
        self.provides = m.get("provides", [])
        self.conflicts = m.get("conflicts", [])
        self.replaces = m.get("replaces", [])
        self.breaks = m.get("breaks", [])
        self.suggests = m.get("suggests", [])
        self.recommends = m.get("recommends", [])

        # 触发器
        trig = m.get("triggers", {})
        self.triggers = {
            "interest": trig.get("interest", []),
            "activate": trig.get("activate", []),
        }

        # 文件列表
        self.files = m.get("files", [])

        # 校验和
        self.checksums = m.get("checksums", {})

    def verify(self) -> Tuple[bool, str]:
        """校验 .oil 完整性"""
        if not self.name:
            return (False, "manifest 缺少 name")
        if not self.version:
            return (False, "manifest 缺少 version")
        # 校验格式版本
        fmt = self.manifest.get("format", "")
        if fmt and not fmt.startswith("oil"):
            return (False, f"格式版本不兼容: {fmt}")
        # 校验 manifest 中的 checksums（如果有）
        if self.checksums and self._tar_data:
            for fname, expected in self.checksums.items():
                h = hashlib.sha256()
                h.update(self._tar_data)
                if h.hexdigest() != expected:
                    return (False, f"校验和失败: {fname}")
        return (True, "OK")

    def get_sha256(self) -> str:
        return hashlib.sha256(self._data).hexdigest()

    def list_files(self) -> List[str]:
        """列出包内文件（不含 manifest 和 scripts）"""
        return [f for f in self.files if not f.startswith(("oil-manifest", "scripts/"))]

    def extract_data(self, dest: str = ".", progress_cb=None) -> List[str]:
        """解压 data/ 目录到目标"""
        if not self._tar_data:
            return []
        installed = []
        with tarfile.open(fileobj=io.BytesIO(self._tar_data), mode="r:") as tf:
            total = len([m for m in tf.getmembers() if m.isfile()])
            count = 0
            for m in tf.getmembers():
                if progress_cb:
                    count += 1
                    progress_cb(count, total, m.name)
                if m.name.startswith("data/"):
                    # 去掉 data/ 前缀
                    rel = m.name[5:]
                    if not rel:
                        continue
                    target = os.path.join(dest, rel)
                    if m.isfile():
                        f = tf.extractfile(m)
                        if f:
                            os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
                            with open(target, "wb") as out:
                                out.write(f.read())
                            installed.append(rel)
                    elif m.isdir():
                        os.makedirs(target, exist_ok=True)
                elif m.name.startswith("scripts/"):
                    continue  # scripts 不写入系统
                elif m.name == "oil-manifest.json":
                    continue
                else:
                    # 其他顶层文件
                    target = os.path.join(dest, m.name)
                    if m.isfile():
                        f = tf.extractfile(m)
                        if f:
                            os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
                            with open(target, "wb") as out:
                                out.write(f.read())
                            installed.append(m.name)
        return installed

    def extract_script(self, script_name: str, dest_path: str) -> bool:
        data = self.maintainer_scripts.get(script_name)
        if not data:
            return False
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(data)
        os.chmod(dest_path, 0o755)
        return True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "arch": self.arch,
            "source_format": "oil",
            "depends": self.depends,
            "provides": self.provides,
            "conflicts": self.conflicts,
            "replaces": self.replaces,
            "breaks": self.breaks,
            "triggers": self.triggers,
            "description": self.description,
            "section": self.section,
            "installed_size": self.installed_size,
            "homepage": self.homepage,
            "sha256": self.get_sha256(),
        }

    def __repr__(self):
        return f"OilPackage({self.name} {self.version} [{self.arch}])"

# === .oil 构建工具 ===

def build_oil_package(
    name: str, version: str, arch: str,
    source_dir: str,  # 要打包的文件目录
    output_path: str,
    description: str = "",
    depends: List[List[str]] = None,
    scripts_dir: str = "",  # 含 preinst/postinst 等
    triggers: Dict[str, List[str]] = None,
    compression: str = "gzip",  # gzip / bzip2 / xz / none
    extra_manifest: Dict = None,
) -> str:
    """
    构建 .oil 包。
    source_dir 结构:
      source_dir/usr/bin/xxx
      source_dir/etc/xxx.conf
      ...
    """
    import gzip, bz2, lzma as lzma_mod

    # 收集文件
    file_list = []
    for root, dirs, files in os.walk(source_dir):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, source_dir)
            file_list.append((rel, full))

    # 计算校验和
    checksums = {}
    for rel, full in file_list:
        h = hashlib.sha256()
        with open(full, "rb") as fh:
            h.update(fh.read())
        checksums[rel] = h.hexdigest()

    # 构建 manifest
    manifest = {
        "name": name,
        "version": version,
        "arch": arch,
        "format": f"oil-{OIL_FORMAT_VERSION}",
        "description": description,
        "depends": depends or [],
        "triggers": triggers or {"interest": [], "activate": []},
        "files": [rel for rel, _ in file_list],
        "checksums": {"manifest": ""},  # 后面填
        "installed_size": sum(os.path.getsize(f) for _, f in file_list),
    }
    if extra_manifest:
        manifest.update(extra_manifest)

    manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
    # manifest 自身的 sha256
    checksums["oil-manifest.json"] = hashlib.sha256(manifest_json).hexdigest()
    manifest["checksums"] = checksums
    manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")

    # 打包 tar
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w") as tf:
        # manifest 第一个
        ti = tarfile.TarInfo(name="oil-manifest.json")
        ti.size = len(manifest_json)
        ti.mtime = int(time.time())
        tf.addfile(ti, io.BytesIO(manifest_json))

        # data/ 下的文件
        for rel, full in file_list:
            tf.add(full, f"data/{rel}")

        # scripts/
        if scripts_dir and os.path.isdir(scripts_dir):
            for s in ["preinst", "postinst", "prerm", "postrm"]:
                sp = os.path.join(scripts_dir, s)
                if os.path.exists(sp):
                    tf.add(sp, f"scripts/{s}")

    tar_data = tar_buf.getvalue()

    # 压缩
    if compression == "gzip":
        import gzip as gz
        final = gz.compress(tar_data, compresslevel=9)
    elif compression == "bzip2":
        import bz2 as bz
        final = bz.compress(tar_data, compresslevel=9)
    elif compression == "xz":
        import lzma as lz
        final = lz.compress(tar_data, preset=9)
    else:
        final = tar_data

    # 写入
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(final)

    return output_path

# === deb → oil 转换 ===

def convert_deb_to_oil(deb_path: str, output_path: str = "",
                       scripts_dir: str = "") -> str:
    """
    将 .deb 转换为 .oil 格式（保留所有信息）
    """
    from .deb import DebPackage

    pkg = DebPackage(path=deb_path)

    # 解压 data.tar 获取文件列表
    import tempfile
    tmpdir = tempfile.mkdtemp()
    try:
        pkg.extract_data(tmpdir)
        # 提取 scripts
        if not scripts_dir:
            scripts_dir = os.path.join(tmpdir, "_scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        for s in ["preinst", "postinst", "prerm", "postrm"]:
            pkg.extract_control_script(s, os.path.join(scripts_dir, s))

        if not output_path:
            output_path = deb_path.replace(".deb", ".oil")

        build_oil_package(
            name=pkg.name,
            version=pkg.version,
            arch=pkg.architecture,
            source_dir=tmpdir,
            output_path=output_path,
            description=pkg.description,
            depends=pkg.depends,
            scripts_dir=scripts_dir,
            triggers=pkg.triggers,
        )
        return output_path
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

# === 统一解析入口 ===

def parse_package(path: str):
    """自动检测格式并解析"""
    with open(path, "rb") as f:
        header = f.read(8)

    if header == b"!<arch>\n":
        from .deb import DebPackage
        return DebPackage(path=path), "deb"
    elif header[:2] == b"\x1f\x8b" or header[:3] == b"BZh":
        # 可能是 .oil (压缩的 tar)
        return OilPackage(path=path), "oil"
    else:
        # 尝试作为 tar 直接打开
        try:
            with tarfile.open(path) as tf:
                # 检查有没有 oil-manifest.json
                names = tf.getnames()
                if any("oil-manifest" in n for n in names):
                    return OilPackage(path=path), "oil"
        except Exception:
            pass
        raise ValueError(f"无法识别的包格式: {path}")

# === CLI ===

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法:")
        print("  python -m xpm_suite.formats.oil <file.oil>      查看信息")
        print("  python -m xpm_suite.formats.oil build <dir> <out.oil>  构建")
        sys.exit(1)

    if sys.argv[1] == "build":
        if len(sys.argv) < 4:
            print("用法: ... build <source_dir> <output.oil> [name] [version] [arch]")
            sys.exit(1)
        src = sys.argv[2]
        out = sys.argv[3]
        name = sys.argv[4] if len(sys.argv) > 4 else os.path.basename(src)
        ver = sys.argv[5] if len(sys.argv) > 5 else "1.0-0"
        arch = sys.argv[6] if len(sys.argv) > 6 else "all"
        result = build_oil_package(name, ver, arch, src, out)
        print(f"✅ 构建完成: {result}")
        print(f"   大小: {os.path.getsize(result)} bytes")
    else:
        pkg = OilPackage(path=sys.argv[1])
        ok, msg = pkg.verify()
        icon = "✅" if ok else "❌"
        print(f"{icon} 校验: {msg}")
        print(f"  包名: {pkg.name}")
        print(f"  版本: {pkg.version}")
        print(f"  架构: {pkg.arch}")
        print(f"  描述: {pkg.description}")
        print(f"  依赖: {pkg.depends}")
        print(f"  文件数: {len(pkg.list_files())}")
        if pkg.maintainer_scripts:
            print(f"  脚本: {list(pkg.maintainer_scripts.keys())}")

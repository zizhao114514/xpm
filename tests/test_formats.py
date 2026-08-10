"""
测试: 包格式解析（ar / tar / deb / oil）
"""

import sys, os, io, gzip, json, hashlib, tarfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from xpm_suite.formats.ar import (
    ar_read_members, ar_extract, verify_deb, AR_MAGIC,
)
from xpm_suite.formats.untar import (
    parse_tar, untar_stream, extract_control_info,
    parse_control_fields, detect_compression, decompress, TarEntry,
)


class TestAr:
    """ar 归档解析"""

    def _make_ar(self, tmp_path, members):
        """构造一个最小的 ar 归档"""
        import struct
        out = io.BytesIO()
        out.write(AR_MAGIC)
        for name, content in members.items():
            # 固定格式 header
            name_b = name.encode().ljust(16, b"\x00")[:16]
            mtime = b"0".ljust(12)
            uid = b"0".ljust(6)
            gid = b"0".ljust(6)
            mode = b"100644".ljust(8)
            size = str(len(content)).ljust(10).encode()
            fmag = b"\x60\n"
            out.write(name_b + mtime + uid + gid + mode + size + fmag)
            out.write(content)
            # 2-byte 对齐
            pad = (len(content) % 2) and b"\x00" or b""
            out.write(pad)
        return out.getvalue()

    def test_verify_deb_valid(self, tmp_path):
        data = self._make_ar(tmp_path, {
            "control.tar.gz": b"fake_control",
            "data.tar.gz": b"fake_data",
        })
        assert verify_deb(data) == True

    def test_verify_deb_invalid(self):
        assert verify_deb(b"not an ar file") == False

    def test_ar_read_members(self, tmp_path):
        data = self._make_ar(tmp_path, {
            "control.tar.gz": b"control_content_123",
            "data.tar.xz": b"data_content_456",
        })
        members = ar_read_members(data)
        assert len(members) == 2
        names = {m.name for m in members}
        assert "control.tar.gz" in names
        assert "data.tar.xz" in names

    def test_ar_extract(self, tmp_path):
        data = self._make_ar(tmp_path, {"hello.txt": b"Hello World!"})
        result = ar_extract(data, "hello.txt")
        assert result == b"Hello World!"


class TestUntar:
    """tar 解析 + 解压"""

    def _make_tar(self, files, compress=None):
        buf = io.BytesIO()
        mode = "w:gz" if compress == "gzip" else "w"
        with tarfile.open(fileobj=buf, mode=mode) as tf:
            for name, content in files.items():
                info = tarfile.TarInfo(name=name)
                info.size = len(content)
                tf.addfile(info, io.BytesIO(content))
        return buf.getvalue()

    def test_parse_tar(self):
        data = self._make_tar({"a.txt": b"AAA", "b.txt": b"BBBBB"})
        entries = parse_tar(data)
        assert len(entries) == 2
        names = {e.name for e in entries}
        assert "a.txt" in names
        assert "b.txt" in names

    def test_parse_tar_gz(self):
        data = self._make_tar({"test.txt": b"hello"}, compress="gzip")
        # 应该能自动处理
        # parse_tar 需要未压缩的 tar
        import gzip as gz
        raw = gz.decompress(data)
        entries = parse_tar(raw)
        assert len(entries) == 1

    def test_detect_compression(self):
        assert detect_compression(b"\x1f\x8bxxxx") == "gzip"
        assert detect_compression(b"BZhxxxx") == "bzip2"
        assert detect_compression(b"\xfd\x37\x7a\x58\x5a\x00") == "xz"
        assert detect_compression(bytes([0x28, 0xb5, 0x2f, 0xfd])) == "zstd"
        assert detect_compression(b"random") == "none"

    def test_untar_stream(self, tmp_path):
        data = self._make_tar({"usr/bin/app": b"#!/bin/sh\necho hi"})
        dest = tmp_path / "extract"
        dest.mkdir()
        files = untar_stream(data, str(dest))
        assert "usr/bin/app" in files
        assert (dest / "usr" / "bin" / "app").exists()

    def test_extract_control_info(self):
        # 构造 control.tar.gz
        import gzip as gz
        control_text = b"Package: testpkg\nVersion: 1.0\nArchitecture: all\n"
        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w") as tf:
            info = tarfile.TarInfo(name="control")
            info.size = len(control_text)
            tf.addfile(info, io.BytesIO(control_text))
        gz_data = gz.compress(tar_buf.getvalue())
        result = extract_control_info(gz_data)
        assert result.get("Package") == "testpkg"
        assert result.get("Version") == "1.0"

    def test_parse_control_fields(self):
        text = "Package: htop\nVersion: 3.4.1-5\nDepends: libc6 (>= 2.34)\n"
        result = parse_control_fields(text)
        assert result["Package"] == "htop"
        assert result["Version"] == "3.4.1-5"
        assert "libc6" in result["Depends"]


class TestDeb:
    """deb 包解析"""

    def _make_minimal_deb(self, tmp_path):
        """构造一个最小化的 .deb 包"""
        # control.tar.gz
        control_text = (
            b"Package: testpkg\n"
            b"Version: 1.0-0\n"
            b"Architecture: all\n"
            b"Description: Test package\n"
            b" A test package for unit tests.\n"
            b"Depends: libc6\n"
        )
        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w") as tf:
            info = tarfile.TarInfo(name="control")
            info.size = len(control_text)
            tf.addfile(info, io.BytesIO(control_text))
        import gzip as gz
        control_tar_gz = gz.compress(tar_buf.getvalue())

        # data.tar.gz
        data_content = b"#!/bin/sh\necho hello"
        tar_buf2 = io.BytesIO()
        with tarfile.open(fileobj=tar_buf2, mode="w") as tf:
            info = tarfile.TarInfo(name="usr/bin/testapp")
            info.size = len(data_content)
            info.mode = 0o755
            tf.addfile(info, io.BytesIO(data_content))
        data_tar_gz = gz.compress(tar_buf2.getvalue())

        # ar 归档
        import struct
        out = io.BytesIO()
        out.write(AR_MAGIC)
        for name, content in [("control.tar.gz", control_tar_gz),
                              ("data.tar.gz", data_tar_gz)]:
            name_b = name.encode().ljust(16, b"\x00")[:16]
            header = (
                name_b +
                b"0".ljust(12) +  # mtime
                b"0".ljust(6) +   # uid
                b"0".ljust(6) +   # gid
                b"100644".ljust(8) + # mode
                str(len(content)).ljust(10).encode() +
                b"\x60\n"
            )
            out.write(header)
            out.write(content)
            if len(content) % 2:
                out.write(b"\x00")
        return out.getvalue()

    def test_parse_deb(self, tmp_path):
        from xpm_suite.formats.deb import DebPackage
        data = self._make_minimal_deb(tmp_path)
        pkg = DebPackage(data=data)
        assert pkg.name == "testpkg"
        assert pkg.version == "1.0-0"
        assert pkg.architecture == "all"
        assert "libc6" in pkg.depends[0][0]

    def test_verify_deb(self, tmp_path):
        from xpm_suite.formats.deb import DebPackage
        data = self._make_minimal_deb(tmp_path)
        pkg = DebPackage(data=data)
        ok, msg = pkg.verify()
        assert ok == True

    def test_list_files(self, tmp_path):
        from xpm_suite.formats.deb import DebPackage
        data = self._make_minimal_deb(tmp_path)
        pkg = DebPackage(data=data)
        files = pkg.list_files()
        assert "usr/bin/testapp" in files

    def test_extract_data(self, tmp_path):
        from xpm_suite.formats.deb import DebPackage
        data = self._make_minimal_deb(tmp_path)
        pkg = DebPackage(data=data)
        dest = tmp_path / "inst"
        dest.mkdir()
        installed = pkg.extract_data(str(dest))
        assert "usr/bin/testapp" in installed
        assert (dest / "usr" / "bin" / "testapp").exists()

    def test_get_sha256(self, tmp_path):
        from xpm_suite.formats.deb import DebPackage
        data = self._make_minimal_deb(tmp_path)
        pkg = DebPackage(data=data)
        sha = pkg.get_sha256()
        assert len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha)

    def test_split_depends(self):
        from xpm_suite.formats.deb import _split_depends
        result = _split_depends("libc6 (>= 2.34), libssl3")
        assert len(result) == 2
        assert "libc6" in result[0][0]
        assert "libssl3" in result[1][0]

    def test_split_depends_with_pipe(self):
        from xpm_suite.formats.deb import _split_depends
        result = _split_depends("apache2 | httpd, libssl3")
        assert len(result) == 2
        assert len(result[0]) == 2  # alternatives


class TestOil:
    """oil 包格式"""

    def _make_oil(self, tmp_path, manifest_extra=None):
        import gzip as gz
        manifest = {
            "name": "testoil",
            "version": "1.0-0",
            "arch": "all",
            "format": "oil-1.0",
            "description": "Test oil package",
            "depends": [["libc6"]],
            "triggers": {"interest": [], "activate": []},
            "files": ["usr/bin/testoil"],
            "installed_size": 100,
        }
        if manifest_extra:
            manifest.update(manifest_extra)

        manifest_json = json.dumps(manifest, indent=2).encode()

        # data files
        files_in_tar = {
            "oil-manifest.json": manifest_json,
            "data/usr/bin/testoil": b"#!/bin/sh\necho oil!",
        }

        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w") as tf:
            for name, content in files_in_tar.items():
                info = tarfile.TarInfo(name=name)
                info.size = len(content)
                if "testoil" in name:
                    info.mode = 0o755
                tf.addfile(info, io.BytesIO(content))

        tar_data = tar_buf.getvalue()
        return gz.compress(tar_data)

    def test_parse_oil(self, tmp_path):
        from xpm_suite.formats.oil import OilPackage
        data = self._make_oil(tmp_path)
        pkg = OilPackage(data=data)
        assert pkg.name == "testoil"
        assert pkg.version == "1.0-0"
        assert pkg.arch == "all"

    def test_verify_oil(self, tmp_path):
        from xpm_suite.formats.oil import OilPackage
        data = self._make_oil(tmp_path)
        pkg = OilPackage(data=data)
        ok, msg = pkg.verify()
        assert ok == True

    def test_oil_extract(self, tmp_path):
        from xpm_suite.formats.oil import OilPackage
        data = self._make_oil(tmp_path)
        pkg = OilPackage(data=data)
        dest = tmp_path / "oil_inst"
        dest.mkdir()
        installed = pkg.extract_data(str(dest))
        assert any("usr/bin/testoil" in f for f in installed)

    def test_oil_to_dict(self, tmp_path):
        from xpm_suite.formats.oil import OilPackage
        data = self._make_oil(tmp_path)
        pkg = OilPackage(data=data)
        d = pkg.to_dict()
        assert d["name"] == "testoil"
        assert d["source_format"] == "oil"

    def test_parse_package_auto(self, tmp_path):
        from xpm_suite.formats.oil import parse_package
        data = self._make_oil(tmp_path)
        pkg_file = tmp_path / "test.oil"
        pkg_file.write_bytes(data)
        pkg, fmt = parse_package(str(pkg_file))
        assert fmt == "oil"
        assert pkg.name == "testoil"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

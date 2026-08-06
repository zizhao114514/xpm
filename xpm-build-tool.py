#!/usr/bin/env python3
"""
xpm-build-tool - XPM .oil 包构建工具 (v2.1-0)
简化版：将一个目录打包成 .oil 格式
"""
import os, sys, hashlib, tarfile, gzip, argparse

def build_oil(directory, output=None):
    """将目录打包为 .oil"""
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        print(f"[✗] 目录不存在: {directory}")
        sys.exit(1)

    # 找 control
    control_path = None
    for root, dirs, files in os.walk(directory):
        if "control" in files:
            control_path = os.path.join(root, "control")
            break

    if not control_path:
        print(f"[✗] 未找到 control 文件")
        sys.exit(1)

    # 读 control
    fields = {}
    with open(control_path) as f:
        for line in f:
            line = line.strip()
            if ":" in line:
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip()

    pkg = fields.get("Package", "unknown")
    ver = fields.get("Version", "0.0")
    arch = fields.get("Architecture", "all")

    if not output:
        output = f"{pkg}_{ver}_{arch}.oil"

    print(f"[i] 构建: {pkg} {ver} ({arch})")

    # 收集文件（排除 control 所在目录下的元文件）
    meta_dir = os.path.dirname(control_path)
    files = []
    for root, dirs, fnames in os.walk(directory):
        for fn in fnames:
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, directory)
            # 跳过元数据目录
            if os.path.abspath(os.path.dirname(fp)).startswith(os.path.abspath(meta_dir)):
                continue
            files.append((fp, rel))

    print(f"[i] 文件数: {len(files)}")

    # 生成 checksums
    checksums = []
    for fp, rel in files:
        h = hashlib.sha256()
        with open(fp, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        checksums.append(f"{h.hexdigest()}  {rel}")

    # 构建 .oil (tar.gz)
    with tarfile.open(output, "w:gz") as tar:
        # data.tar.gz
        data_path = output + ".data.tar.gz"
        with tarfile.open(data_path, "w:gz") as dt:
            for fp, rel in files:
                dt.add(fp, arcname=rel)
        tar.add(data_path, arcname="data.tar.gz")
        os.remove(data_path)

        # control
        tar.add(control_path, arcname="control")

        # checksums
        import io
        cs_bytes = "\n".join(checksums).encode()
        cs_info = tarfile.TarInfo(name="checksums.sha256")
        cs_info.size = len(cs_bytes)
        tar.addfile(cs_info, io.BytesIO(cs_bytes))

    size = os.path.getsize(output)
    print(f"[✓] 构建完成: {output} ({size} bytes)")
    return output

def main():
    parser = argparse.ArgumentParser(description="XPM .oil 包构建工具")
    parser.add_argument("directory", help="包含程序文件的目录")
    parser.add_argument("-o", "--output", help="输出 .oil 文件路径")
    args = parser.parse_args()

    build_oil(args.directory, args.output)

if __name__ == "__main__":
    main()

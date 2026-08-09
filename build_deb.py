#!/usr/bin/env python3
"""
构建 XPM Suite .deb 安装包
包含: xpm + xstore + xstore-gui + 配置 + 文档

使用纯 Python 构建（不依赖 dpkg-deb），兼容受限环境。
"""

import os, shutil, stat, tarfile, io, hashlib, json, time, sys
from pathlib import Path

# === 配置 ===

PKG_NAME = "xpm-suite"
VERSION = "3.0.0"
ARCH = "all"
MAINTAINER = "Zizhao <zizhao@example.com>"
DESCRIPTION = (
    "XPM Suite - 统一包管理器 + 应用商店\n"
    " 包含:\n"
    "  - xpm: 包管理器（索引/依赖/下载/安装/回滚/触发器）\n"
    "  - xstore: 应用商店命令行\n"
    "  - xstore-gui: 图形化应用商店（深色主题/卡片布局）\n"
    "  - 支持 .deb 和 .oil 双格式\n"
    "  - 多线程下载/断点续传/镜像切换\n"
    "  - 纯 Python 实现，零外部依赖"
)

SRC_ROOT = Path("/data/workspace/xpm-suite")
PYTHON_SRC = SRC_ROOT / "src" / "xpm_suite"
PACKAGING = SRC_ROOT / "packaging"
BUILD_DIR = SRC_ROOT / "build"
DEB_ROOT = BUILD_DIR / f"{PKG_NAME}_{VERSION}_all"

# === 工具函数 ===

def set_mode(path, mode):
    """设置文件/目录权限（兼容 overlayfs）"""
    try:
        os.chmod(str(path), mode)
    except OSError:
        pass

def clean():
    global DEB_ROOT
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)
    set_mode(BUILD_DIR, 0o755)
    DEB_ROOT = BUILD_DIR / f"{PKG_NAME}_{VERSION}_all"
    DEB_ROOT.mkdir(parents=True)
    set_mode(DEB_ROOT, 0o755)

def write_text(path, content, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    set_mode(path, mode)

def write_bytes(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)
    set_mode(path, mode)

# === 构建步骤 ===

def create_debian_control():
    """创建 DEBIAN/control + postinst + prerm"""
    deb_dir = DEB_ROOT / "DEBIAN"
    deb_dir.mkdir(parents=True, exist_ok=True)
    set_mode(deb_dir, 0o755)

    control = f"""Package: {PKG_NAME}
Version: {VERSION}
Section: admin
Priority: optional
Architecture: {ARCH}
Depends: python3 (>=3.8), python3-tk (>=3.8) | tk, dpkg (>=1.16)
Recommends: curl, wget
Suggests: python3-requests
Maintainer: {MAINTAINER}
Homepage: https://github.com/zizhao114514/xpm
Description: {DESCRIPTION}
"""
    write_text(deb_dir / "control", control, 0o644)

    postinst = """#!/bin/bash
set -e
echo "🏪 XPM Suite 安装完成"
echo "   版本: 3.0.0 Add Gui Store Edition"
echo ""
echo "快速开始:"
echo "  xpm version          # 查看版本"
echo "  xpm arch             # 查看架构"
echo "  xpm update           # 更新索引"
echo "  xpm install htop     # 安装包"
echo "  xstore               # 应用商店 CLI"
echo "  xstore-gui           # 图形应用商店"
echo ""
mkdir -p /etc/xpm/sources.list.d
mkdir -p /var/cache/xpm
mkdir -p /var/lib/xpm/info
mkdir -p /var/lib/xstore
if [ ! -f /etc/xpm/sources.list.d/tuna.list ]; then
    cat > /etc/xpm/sources.list.d/tuna.list << 'EOF'
# XPM Suite 默认软件源 - 清华大学镜像
deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main
deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie-updates main
EOF
fi
echo "✅ 初始化完成"
"""
    write_text(deb_dir / "postinst", postinst, 0o755)

    prerm = """#!/bin/bash
set -e
echo "🗑️  正在卸载 XPM Suite..."
"""
    write_text(deb_dir / "prerm", prerm, 0o755)

def install_python_module():
    """安装 Python 模块到 /usr/local/share/xpm-suite/"""
    dest = DEB_ROOT / "usr" / "local" / "share" / "xpm-suite" / "xpm_suite"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(str(PYTHON_SRC), str(dest))

    # 删除 __pycache__
    for pyc in dest.rglob("__pycache__"):
        shutil.rmtree(pyc, ignore_errors=True)
    for pyc in dest.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)

    # 设置权限
    for f in dest.rglob("*.py"):
        set_mode(f, 0o644)
    for d in dest.rglob("*"):
        if d.is_dir():
            set_mode(d, 0o755)

def install_binaries():
    """安装可执行脚本到 /usr/local/bin/"""
    bin_dir = DEB_ROOT / "usr" / "local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    set_mode(bin_dir, 0o755)

    scripts = {
        "xpm": '''#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/local/share/xpm-suite")
from xpm_suite.cli.xpm_main import main
sys.exit(main())
''',
        "xstore": '''#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/local/share/xpm-suite")
from xpm_suite.store.cli import main
sys.exit(main())
''',
        "xstore-gui": '''#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/local/share/xpm-suite")
from xpm_suite.store.gui.app import run_gui
sys.exit(run_gui())
''',
    }

    for name, content in scripts.items():
        path = bin_dir / name
        write_text(path, content, 0o755)

def install_desktop():
    """安装 .desktop 文件"""
    app_dir = DEB_ROOT / "usr" / "share" / "applications"
    app_dir.mkdir(parents=True, exist_ok=True)
    set_mode(app_dir, 0o755)
    src_desktop = PACKAGING / "xstore-gui.desktop"
    if src_desktop.exists():
        shutil.copy2(str(src_desktop), str(app_dir / "xstore-gui.desktop"))
        set_mode(app_dir / "xstore-gui.desktop", 0o644)

def install_docs():
    """安装文档"""
    doc_dir = DEB_ROOT / "usr" / "share" / "doc" / PKG_NAME
    doc_dir.mkdir(parents=True, exist_ok=True)
    set_mode(doc_dir, 0o755)

    readme = """XPM Suite v3.0.0 "Add Gui Store Edition"
============================================

统一包管理器 + 应用商店

快速开始:
  xpm version          # 查看版本
  xpm arch             # 架构信息
  xpm update           # 更新索引
  xpm install htop     # 安装包
  xpm search curl      # 搜索
  xpm list             # 已安装
  xpm doctor           # 系统诊断

  xstore               # 应用商店 CLI
  xstore browse        # 浏览分类
  xstore top           # 热门排行
  xstore search git    # 搜索
  xstore info htop     # 详情
  xstore install htop  # 安装
  xstore rate htop 5   # 评分

  xstore-gui           # 图形界面

功能特性:
  ✅ 纯 Python 实现，零外部依赖
  ✅ 支持 .deb 和 .oil 双格式
  ✅ 多线程分块下载 + 断点续传
  ✅ 镜像自动切换 + 指数退避
  ✅ 事务安装（全成/全回滚）
  ✅ 触发器引擎（纯 Python）
  ✅ 版本锁定/快照/恢复
  ✅ 智能架构探测（三源兜底）
  ✅ 应用商店 GUI（深色主题）
  ✅ 功能按版本解锁

版本策略:
  v1.x - 基础安装
  v2.x - 架构探测 + 下载器 + xstore CLI
  v3.0 - 事务 + 触发器 + .oil + GUI
  v3.1 - 并行安装 + 主题系统
  v4.0 - 插件系统

GitHub: https://github.com/zizhao114514/xpm
"""
    write_text(doc_dir / "README", readme, 0o644)

    changelog = f"""xpm-suite ({VERSION}) stable; urgency=medium

  * XPM + X-Store 合并为统一项目
  * 新增事务安装引擎（全成/全回滚）
  * 新增触发器引擎（纯 Python）
  * 新增 .oil 原生包格式
  * 新增 X-Store GUI（深色主题/卡片布局）
  * 新增功能开关（版本不达标自动禁用）
  * 架构探测三源兜底（dpkg/uname/cpuinfo）
  * 多线程分块下载 + 断点续传
  * 镜像自动切换 + 指数退避
  * maintainer scripts 完整 DPKG_ 环境

 -- Zizhao <zizhao@example.com>  Sat, 08 Aug 2026 12:00:00 +0000
"""
    write_text(doc_dir / "changelog", changelog, 0o644)

# === 纯 Python .deb 构建 ===
# .deb = ar 归档:
#   debian-binary (文本 "2.0\n")
#   control.tar.gz (DEBIAN/ 内容)
#   data.tar.gz  (usr/ etc/ var/ 内容)

def tar_gz_from_dir(src_dir: Path) -> bytes:
    """将目录打包为 tar.gz 字节"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for root, dirs, files in os.walk(src_dir):
            for d in sorted(dirs):
                full = os.path.join(root, d)
                arcname = os.path.relpath(full, src_dir) + "/"
                ti = tarfile.TarInfo(name=arcname)
                ti.type = tarfile.DIRTYPE
                ti.mode = 0o755
                ti.mtime = int(time.time())
                tar.addfile(ti)
            for f in sorted(files):
                full = os.path.join(root, f)
                arcname = os.path.relpath(full, src_dir)
                ti = tarfile.TarInfo(name=arcname)
                ti.size = os.path.getsize(full)
                ti.mode = 0o644
                ti.mtime = int(time.time())
                with open(full, 'rb') as fh:
                    tar.addfile(ti, fh)
    return buf.getvalue()

def build_ar_archive(debian_binary: bytes, control_tar: bytes, data_tar: bytes) -> bytes:
    """构建 ar 归档 (Debian .deb 格式)"""
    out = io.BytesIO()
    out.write(b"!<arch>\n")

    def write_ar_member(name: str, content: bytes):
        # ar header: name(16) mtime(12) uid(6) gid(6) mode(8) size(10) magic(2)
        name_b = name.encode('ascii').ljust(16, b' ')
        mtime_b = str(int(time.time())).encode().rjust(12, b'0')
        uid_b = b'0     '
        gid_b = b'0     '
        mode_b = b'100644  '
        size_b = str(len(content)).encode().rjust(10, b' ')
        magic = b'`\n'
        header = name_b + mtime_b + uid_b + gid_b + mode_b + size_b + magic
        out.write(header)
        out.write(content)
        # 2-byte padding
        if len(content) % 2 != 0:
            out.write(b'\n')

    write_ar_member("debian-binary", debian_binary)
    write_ar_member("control.tar.gz", control_tar)
    write_ar_member("data.tar.gz", data_tar)
    return out.getvalue()

def build_deb():
    """构建 .deb 文件（纯 Python，不依赖 dpkg-deb）"""
    clean()
    print("📦 构建 XPM Suite .deb 包...")
    print(f"   版本: {VERSION}")
    print(f"   架构: {ARCH}")
    print(f"   代号: Add Gui Store Edition")

    # 1. 准备文件
    create_debian_control()
    print("  ✅ DEBIAN/control + postinst + prerm")

    install_python_module()
    print("  ✅ Python 模块 → /usr/local/share/xpm-suite/")

    install_binaries()
    print("  ✅ 可执行文件 → /usr/local/bin/ (xpm, xstore, xstore-gui)")

    install_desktop()
    print("  ✅ .desktop → /usr/share/applications/")

    install_docs()
    print("  ✅ 文档 → /usr/share/doc/xpm-suite/")

    # 2. 统计
    total_size = 0
    file_count = 0
    for root, dirs, files in os.walk(DEB_ROOT):
        for f in files:
            fp = os.path.join(root, f)
            total_size += os.path.getsize(fp)
            file_count += 1
    print(f"\n  📊 统计: {file_count} 个文件, {total_size/1024:.1f} KB")

    # 3. 构建 tar.gz 成员
    control_dir = DEB_ROOT / "DEBIAN"
    # data 部分 = DEB_ROOT 去掉 DEBIAN/
    data_root = DEB_ROOT  # tar 会包含 DEBIAN 也要去掉... 不对，data.tar 不含 DEBIAN
    # 我们重新组织：把非 DEBIAN 内容放到临时目录
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # data 内容
        data_tmp = tmp_path / "data"
        for item in DEB_ROOT.iterdir():
            if item.name == "DEBIAN":
                continue
            dest = data_tmp / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        print("  📦 打包 control.tar.gz ...")
        control_tar = tar_gz_from_dir(control_dir)
        print("  📦 打包 data.tar.gz ...")
        data_tar = tar_gz_from_dir(data_tmp)

    debian_binary = b"2.0\n"

    print("  📦 组装 .deb (ar 归档) ...")
    deb_data = build_ar_archive(debian_binary, control_tar, data_tar)

    # 4. 写入输出
    output = SRC_ROOT / f"{PKG_NAME}_{VERSION}_all.deb"
    write_bytes(output, deb_data, 0o644)

    size = output.stat().st_size
    print(f"\n  🎉 构建完成: {output}")
    print(f"     大小: {size/1024:.1f} KB")

    # 5. 验证
    print("\n  🔍 验证 .deb ...")
    if deb_data[:8] == b"!<arch>\n":
        print("  ✅ ar magic 正确")
    else:
        print("  ❌ ar magic 错误")
        return None

    # 验证内含文件
    import struct
    pos = 8
    members = []
    while pos < len(deb_data):
        header = deb_data[pos:pos+60]
        name = header[:16].rstrip(b' ').rstrip(b'/').decode('ascii', errors='replace')
        size = int(header[48:58].strip().decode('ascii', errors='replace') or '0')
        pos += 60
        data_start = pos
        pos += size
        if size % 2 != 0:
            pos += 1
        members.append((name, size))

    for name, size in members:
        print(f"    📄 {name:<25} {size:>8} bytes")

    expected = {"debian-binary", "control.tar.gz", "data.tar.gz"}
    found = {m[0] for m in members}
    if expected.issubset(found):
        print("  ✅ 包含必要成员 (debian-binary, control.tar.gz, data.tar.gz)")
    else:
        missing = expected - found
        print(f"  ⚠️ 缺少: {missing}")

    print(f"\n  安装: sudo dpkg -i {output.name}")
    return output

if __name__ == "__main__":
    result = build_deb()
    if result:
        print(f"\n✅ 输出: {result}")
        sys.exit(0)
    else:
        print("\n❌ 构建失败")
        sys.exit(1)

#!/usr/bin/env python3
"""
构建 XPM Suite v3.1.1 .deb 安装包
包含: xpm + xstore + xstore-gui + PAM认证 + 自更新 + 提权 + 软件源管理
使用纯 Python 构建（不依赖 dpkg-deb），兼容受限环境。
"""

import os, shutil, stat, tarfile, io, hashlib, json, time, sys
from pathlib import Path

# === 配置 ===

PKG_NAME = "xpm-suite"
VERSION = "3.1.1"
ARCH = "all"
MAINTAINER = "Zizhao <zizhao@example.com>"
DESCRIPTION = (
    "XPM Suite v3.1.1 - 统一包管理器 + 应用商店\n"
    " 包含:\n"
    "  - xpm: 包管理器（索引/依赖/下载/安装/回滚/触发器）\n"
    "  - xstore: 应用商店命令行\n"
    "  - xstore-gui: 图形化应用商店（深色主题/卡片布局）\n"
    "  - PAM 认证模块（密码验证/会话管理/授权日志）\n"
    "  - 自更新引擎（远程版本检查/自动下载/回滚）\n"
    "  - 提权包装器（sudo/gksu/pkexec 自动选择）\n"
    "  - 软件源管理（sources.list.d/ 标准目录结构）\n"
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

# === DEBIAN 控制文件 ===

def create_debian_control():
    deb_dir = DEB_ROOT / "DEBIAN"
    deb_dir.mkdir(parents=True, exist_ok=True)
    set_mode(deb_dir, 0o755)

    control = f"""Package: {PKG_NAME}
Version: {VERSION}
Section: admin
Priority: optional
Architecture: {ARCH}
Depends: python3 (>=3.8), python3-tk (>=3.8) | tk, dpkg (>=1.16)
Recommends: curl, wget, sudo, policykit-1
Suggests: python3-requests, gksu
Maintainer: {MAINTAINER}
Homepage: https://github.com/zizhao114514/xpm
Description: {DESCRIPTION}
"""
    write_text(deb_dir / "control", control, 0o644)

    postinst = """#!/bin/bash
set -e
echo "🏪 XPM Suite v{VERSION} 安装完成"
echo ""
echo "快速开始:"
echo "  xpm version          # 查看版本+权限状态"
echo "  xpm auth status      # 查看认证状态"
echo "  xpm update           # 更新索引"
echo "  xpm install htop     # 安装包"
echo "  xstore               # 应用商店 CLI"
echo "  xstore-gui           # 图形应用商店"
echo "  xpm self-update check # 检查更新"
echo ""
echo "首次使用建议:"
echo "  sudo xpm auth install-pam  # 安装 PAM 配置"
echo "  sudo xpm doctor           # 系统诊断"
echo ""
mkdir -p /etc/xpm/sources.list.d
mkdir -p /var/cache/xpm
mkdir -p /var/lib/xpm/info
mkdir -p /var/lib/xpm/backups
mkdir -p /etc/xpm/auth

# 自动探测架构，写入带 [arch=xxx] 的源
if [ ! -f /etc/xpm/sources.list.d/tuna.list ]; then
    # 探测架构
    ARCH="amd64"
    if command -v dpkg >/dev/null 2>&1; then
        ARCH=$(dpkg --print-architecture 2>/dev/null || echo "amd64")
    elif command -v uname >/dev/null 2>&1; then
        case "$(uname -m)" in
            x86_64)  ARCH="amd64" ;;
            aarch64)  ARCH="arm64" ;;
            armv7l)   ARCH="armhf" ;;
            armv6l)   ARCH="armel" ;;
            i686)     ARCH="i386"  ;;
            loongarch64) ARCH="loong64" ;;
            riscv64)  ARCH="riscv64" ;;
            ppc64le)  ARCH="ppc64el" ;;
            s390x)    ARCH="s390x" ;;
        esac
    fi

    cat > /etc/xpm/sources.list.d/tuna.list << EOF
# XPM Suite 默认软件源 - 清华大学镜像
# 架构自动探测: $ARCH
deb [arch=$ARCH] https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main contrib non-free non-free-firmware
deb [arch=$ARCH] https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie-updates main contrib non-free non-free-firmware
EOF
    echo "  ✅ 默认源已写入 (arch=$ARCH)"
fi
echo "✅ XPM Suite v{VERSION} 初始化完成"
"""
    write_text(deb_dir / "postinst", postinst, 0o755)

    prerm = """#!/bin/bash
set -e
echo "🗑️  正在卸载 XPM Suite..."
"""
    write_text(deb_dir / "prerm", prerm, 0o755)

# === Python 模块 ===

def install_python_module():
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

    # 验证新模块存在
    assert (dest / "core" / "auth.py").exists(), "auth.py missing!"
    assert (dest / "core" / "self_update.py").exists(), "self_update.py missing!"
    assert (dest / "core" / "elevate.py").exists(), "elevate.py missing!"
    print("  ✅ 新模块: auth.py / self_update.py / elevate.py")

# === 可执行脚本 ===

def install_binaries():
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

# === .desktop 文件 ===

def install_desktop():
    app_dir = DEB_ROOT / "usr" / "share" / "applications"
    app_dir.mkdir(parents=True, exist_ok=True)
    set_mode(app_dir, 0o755)
    src_desktop = PACKAGING / "xstore-gui.desktop"
    if src_desktop.exists():
        shutil.copy2(str(src_desktop), str(app_dir / "xstore-gui.desktop"))
        set_mode(app_dir / "xstore-gui.desktop", 0o644)

# === PAM 配置 ===

def install_pam_config():
    """安装 PAM 服务配置到 .deb 中"""
    pam_dir = DEB_ROOT / "etc" / "pam.d"
    pam_dir.mkdir(parents=True, exist_ok=True)
    set_mode(pam_dir, 0o755)

    pam_config = """# XPM Suite PAM 配置
# 允许本地用户通过密码认证执行包管理操作

auth    required    pam_unix.so
auth    optional    pam_permit.so

account required    pam_unix.so
account optional    pam_permit.so

password required   pam_unix.so

session required    pam_limits.so
session optional    pam_unix.so
"""
    write_text(pam_dir / "xpm", pam_config, 0o644)
    print("  ✅ PAM 配置: /etc/pam.d/xpm")

# === 文档 ===

def install_docs():
    doc_dir = DEB_ROOT / "usr" / "share" / "doc" / PKG_NAME
    doc_dir.mkdir(parents=True, exist_ok=True)
    set_mode(doc_dir, 0o755)

    readme = f"""XPM Suite v{VERSION} "Add Gui Store Edition"
============================================

统一包管理器 + 应用商店（PAM 认证 + 自更新 + 提权）

快速开始:
  xpm version              # 查看版本 + 权限状态
  xpm auth status          # 查看认证状态
  xpm auth install-pam     # 安装 PAM 配置（首次）
  xpm update               # 更新索引
  xpm install htop         # 安装包（需认证）
  xpm search curl          # 搜索
  xpm list                 # 已安装
  xpm doctor               # 系统诊断
  xpm self-update check    # 检查 XPM 自身更新

  xstore                   # 应用商店 CLI
  xstore browse            # 浏览分类
  xstore top               # 热门排行
  xstore search git        # 搜索
  xstore info htop         # 详情
  xstore install htop      # 安装（需认证）
  xstore rate htop 5       # 评分

  xstore-gui               # 图形界面（需 sudo/gksu）
  sudo xstore-gui           # 推荐启动方式

功能特性:
  ✅ PAM 密码认证（安装/卸载/更新前验证）
  ✅ 会话缓存（避免重复输入密码）
  ✅ 授权日志（/etc/xpm/auth/auth.log）
  ✅ 自更新引擎（远程版本检查 + 自动下载 + 回滚）
  ✅ 提权包装器（sudo/gksu/pkexec 自动选择）
  ✅ 支持 .deb 和 .oil 双格式
  ✅ 多线程分块下载 + 断点续传
  ✅ 镜像自动切换 + 指数退避
  ✅ 事务安装（全成/全回滚）
  ✅ 触发器引擎（纯 Python）
  ✅ 版本锁定/快照/恢复
  ✅ 智能架构探测（三源兜底）
  ✅ 应用商店 GUI（深色主题 + 卡片布局）
  ✅ 功能按版本解锁

安全设计:
  🔐 安装/卸载/更新 → 需要 PAM 认证
  🔐 自更新 → critical 级别（最严格）
  🔐 会话有效期：low=5min, medium=3min, high=2min, critical=1min
  🔐 认证失败 3 次锁定
  🔐 所有提权操作记录日志

版本策略:
  v1.x - 基础安装
  v2.x - 架构探测 + 下载器 + xstore CLI
  v3.0 - 事务 + 触发器 + .oil + GUI
  v3.1 - PAM 认证 + 自更新 + 提权（当前）
  v4.0 - 插件系统

GitHub: https://github.com/zizhao114514/xpm
"""
    write_text(doc_dir / "README", readme, 0o644)

    changelog = f"""xpm-suite ({VERSION}) stable; urgency=medium

  * 新增 PAM 认证模块（密码验证/会话管理/授权日志）
  * 新增自更新引擎（远程版本检查/自动下载/回滚）
  * 新增提权包装器（sudo/gksu/pkexec 自动选择）
  * 所有安装/卸载/更新操作强制 PAM 认证
  * 新增 xpm auth 命令（status/install-pam/log/clear）
  * 新增 xpm self-update 命令（check/install/rollback/backups）
  * 新增 xpm elevate 命令（status/re-exec/menu）
  * GUI 启动时自动检查更新
  * GUI 安装/卸载前检查 root 权限
  * 版本号升级到 3.1.0

 -- Zizhao <zizhao@example.com>  Mon, 10 Aug 2026 12:00:00 +0000
"""
    write_text(doc_dir / "changelog", changelog, 0o644)

# === 纯 Python .deb 构建 ===

def tar_gz_from_dir(src_dir: Path) -> bytes:
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
                # 保留可执行权限：检查文件自身的 mode 位
                file_mode = os.stat(full).st_mode
                if file_mode & 0o111:  # 任意执行位被设置
                    ti.mode = 0o755
                else:
                    ti.mode = 0o644
                ti.mtime = int(time.time())
                # 设置 tar 内的 owner/组为 root
                ti.uid = 0
                ti.gid = 0
                ti.uname = "root"
                ti.gname = "root"
                with open(full, 'rb') as fh:
                    tar.addfile(ti, fh)
    return buf.getvalue()

def build_ar_archive(debian_binary: bytes, control_tar: bytes, data_tar: bytes) -> bytes:
    out = io.BytesIO()
    out.write(b"!<arch>\n")

    def write_ar_member(name: str, content: bytes):
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
        if len(content) % 2 != 0:
            out.write(b'\n')

    write_ar_member("debian-binary", debian_binary)
    write_ar_member("control.tar.gz", control_tar)
    write_ar_member("data.tar.gz", data_tar)
    return out.getvalue()

def build_deb():
    clean()
    print(f"📦 构建 XPM Suite v{VERSION} .deb 包...")
    print(f"   代号: Add Gui Store Edition")
    print(f"   架构: {ARCH}")
    print(f"   新增: PAM 认证 + 自更新 + 提权\n")

    # 1. 准备文件
    create_debian_control()
    print("  ✅ DEBIAN/control + postinst + prerm")

    install_python_module()
    print("  ✅ Python 模块 → /usr/local/share/xpm-suite/")

    install_binaries()
    print("  ✅ 可执行文件 → /usr/local/bin/ (xpm, xstore, xstore-gui)")

    install_desktop()
    print("  ✅ .desktop → /usr/share/applications/")

    install_pam_config()

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

    # 3. 构建 tar.gz
    control_dir = DEB_ROOT / "DEBIAN"
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
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

    # 6. 计算 SHA256
    h = hashlib.sha256()
    with open(output, 'rb') as f:
        while True:
            chunk = f.read(64*1024)
            if not chunk: break
            h.update(chunk)
    print(f"  🔐 SHA256: {h.hexdigest()}")

    print(f"\n  安装: sudo dpkg -i {output.name}")
    print(f"  然后: sudo xpm auth install-pam")
    return output

if __name__ == "__main__":
    result = build_deb()
    if result:
        print(f"\n✅ 输出: {result}")
        sys.exit(0)
    else:
        print("\n❌ 构建失败")
        sys.exit(1)

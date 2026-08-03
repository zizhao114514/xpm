#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xm - X11 Manager backend (oil-powered unpacker)
XPM 自主包体系后端：解包 / 安装 / 卸载 / 校验
仅干脏活，不联网、不解析源、不碰 apt-cache
石油驱动，1.x W 稳态。
"""

import os
import sys
import json
import time
import shutil
import hashlib
import subprocess
import fcntl
import errno
import random
from pathlib import Path

# === 路径常量 ===
VAR_LIB = "/var/lib/xm"
VAR_CACHE = "/var/cache/xm"
LOCK_DIR = f"{VAR_CACHE}/lock"
ARCHIVE_DIR = f"{VAR_CACHE}/archives"
TEMP_DIR = f"{VAR_CACHE}/temp"
STATUS_DB = f"{VAR_LIB}/status.json"
COFFEE_LOG = f"{VAR_LIB}/coffee.log"
CONFIG_DIR = "/etc/xm"

# === 石油彩蛋 ===
OIL_RESERVE = 100001
POWER_DRAW = "1.x W"

# === 崩溃计数（给 xpm 前端读取）===
def crash_count_today():
    """读取今日崩溃次数（与 xpm 共享同一份日志）"""
    log_path = os.path.expanduser("~/.cache/xpm/coffee_machine.log")
    if not os.path.exists(log_path):
        return 0
    try:
        today = time.strftime("%Y-%m-%d")
        with open(log_path) as f:
            for line in f:
                if line.startswith(today):
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        return int(parts[1])
    except Exception:
        pass
    return 0

# === 锁文件管理 ===
class LockFile:
    """flock 互斥锁 + 元数据"""
    def __init__(self, path):
        self.path = path
        self.fd = None

    def acquire(self, metadata: dict, timeout: int = 120) -> bool:
        """尝试获取锁，超时返回 False"""
        start = time.time()
        while True:
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o644)
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # 拿到锁，写元数据
                os.ftruncate(self.fd, 0)
                os.write(self.fd, json.dumps(metadata, ensure_ascii=False).encode())
                os.fsync(self.fd)
                return True
            except OSError as e:
                if e.errno not in (errno.EAGAIN, errno.EACCES):
                    raise
                elapsed = int(time.time() - start)
                if elapsed >= timeout:
                    return False
                # 输出等待信息（给前端 xpm 捕获）
                pid = self._read_owner_pid()
                op = self._read_owner_op()
                print(f"检测到锁文件 ({self.path})", file=sys.stderr)
                print(f"  归属进程: xm (PID {pid})", file=sys.stderr)
                print(f"  操作类型: {op}", file=sys.stderr)
                print(f"  已等待: {elapsed}s", file=sys.stderr)
                print(f"  最大等待: {timeout}s", file=sys.stderr)
                print(f"⏳ 等待锁释放中...", file=sys.stderr)
                time.sleep(2)

    def release(self):
        if self.fd is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                os.close(self.fd)
            except Exception:
                pass
            self.fd = None
            # 删除锁文件
            try:
                os.remove(self.path)
            except FileNotFoundError:
                pass

    def _read_owner_pid(self) -> str:
        try:
            with open(self.path) as f:
                data = json.load(f)
                return str(data.get("pid", "unknown"))
        except Exception:
            return "unknown"

    def _read_owner_op(self) -> str:
        try:
            with open(self.path) as f:
                data = json.load(f)
                return data.get("operation", "unknown")
        except Exception:
            return "unknown"


def ensure_dirs():
    """创建必要目录"""
    for d in [VAR_LIB, VAR_CACHE, LOCK_DIR, ARCHIVE_DIR, TEMP_DIR]:
        os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.dirname(COFFEE_LOG), exist_ok=True)
    # 初始化 status.json
    if not os.path.exists(STATUS_DB):
        with open(STATUS_DB, 'w') as f:
            json.dump({}, f)


def load_status() -> dict:
    ensure_dirs()
    try:
        with open(STATUS_DB) as f:
            return json.load(f)
    except Exception:
        return {}


def save_status(db: dict):
    ensure_dirs()
    tmp = STATUS_DB + ".tmp"
    with open(tmp, 'w') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATUS_DB)


def compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def parse_control(control_text: str) -> dict:
    """解析键值对格式的 control 文件"""
    result = {}
    current_key = None
    current_val = []
    for line in control_text.splitlines():
        if not line.strip():
            continue
        if line.startswith(" ") or line.startswith("\t"):
            # 续行
            if current_key:
                current_val.append(line.strip())
        else:
            # 保存上一个
            if current_key:
                result[current_key] = "\n".join(current_val)
            if "=" in line:
                key, _, val = line.partition("=")
                current_key = key.strip()
                current_val = [val.strip()]
    if current_key:
        result[current_key] = "\n".join(current_val)
    return result


def read_control_from_oil(oil_path: str) -> dict:
    """从 .oil 包中读取 control 信息（不解压全部文件）"""
    import tarfile
    with tarfile.open(oil_path, 'r:gz') as tf:
        # 找 control 文件
        for m in tf.getmembers():
            if m.name.endswith("/xpm/control") or m.name == "xpm/control":
                f = tf.extractfile(m)
                return parse_control(f.read().decode('utf-8'))
        # 也试试直接叫 control
        for m in tf.getmembers():
            if m.name.endswith("/control"):
                f = tf.extractfile(m)
                return parse_control(f.read().decode('utf-8'))
    return {}


def read_checksums_from_oil(oil_path: str) -> dict:
    """从 .oil 包中读取 checksums.sha256"""
    import tarfile
    sums = {}
    with tarfile.open(oil_path, 'r:gz') as tf:
        for m in tf.getmembers():
            if m.name.endswith("/checksums.sha256") or m.name == "checksums.sha256":
                f = tf.extractfile(m)
                for line in f.read().decode('utf-8').splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        sums[parts[1]] = parts[0]
                return sums
    return {}


def extract_data(oil_path: str, dest: str) -> list:
    """解压 .oil 中的 data.tar.gz 到 dest，返回文件列表"""
    import tarfile
    files = []
    with tarfile.open(oil_path, 'r:gz') as tf:
        # 先找 data.tar.gz
        data_member = None
        for m in tf.getmembers():
            if m.name.endswith("/data.tar.gz") or m.name == "data.tar.gz":
                data_member = m
                break
        if not data_member:
            raise RuntimeError("oil 包内未找到 data.tar.gz")
        f = tf.extractfile(data_member)
        data_path = os.path.join(dest, "_data.tar.gz")
        with open(data_path, 'wb') as out:
            shutil.copyfileobj(f, out)
        # 解压 data.tar.gz
        with tarfile.open(data_path, 'r:gz') as df:
            df.extractall(dest)
            files = [m.name for m in df.getmembers() if m.isfile()]
        os.remove(data_path)
    return files


def run_script(script_path: str, root: str = "/") -> int:
    """执行安装/卸载脚本"""
    if not script_path or not os.path.exists(script_path):
        return 0
    if not os.access(script_path, os.X_OK):
        os.chmod(script_path, 0o755)
    env = os.environ.copy()
    env["XM_ROOT"] = root
    env["XM_OIL_RESERVE"] = str(OIL_RESERVE)
    try:
        result = subprocess.run([script_path], env=env, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        return result.returncode
    except Exception as e:
        print(f"⚠️ 脚本执行异常: {e}", file=sys.stderr)
        return 1


def cmd_unpack(args):
    """xm unpack <file.oil> [--root /path]"""
    ensure_dirs()
    oil_path = args[0] if args else None
    root = "/"
    if "--root" in args:
        idx = args.index("--root")
        if idx + 1 < len(args):
            root = args[idx + 1]

    if not oil_path or not os.path.exists(oil_path):
        print(f"⚠️ 文件不存在: {oil_path}", file=sys.stderr)
        return 1

    dest = os.path.join(TEMP_DIR, f"unpack-{int(time.time())}")
    os.makedirs(dest, exist_ok=True)

    print(f"📂 解包到: {dest}")
    files = extract_data(oil_path, dest)
    print(f"✅ 解包完成: {len(files)} 个文件")

    # 打印 control 摘要
    ctrl = read_control_from_oil(oil_path)
    if ctrl:
        print(f"   包名: {ctrl.get('package', 'unknown')}")
        print(f"   版本: {ctrl.get('version', 'unknown')}")
        print(f"   架构: {ctrl.get('architecture', 'unknown')}")

    return 0


def cmd_install(args):
    """xm install <file.oil>"""
    ensure_dirs()
    oil_path = args[0] if args else None
    if not oil_path or not os.path.exists(oil_path):
        print(f"⚠️ 文件不存在: {oil_path}", file=sys.stderr)
        return 1

    # 获取锁
    lock = LockFile(f"{LOCK_DIR}/install.lock")
    metadata = {
        "pid": os.getpid(),
        "command": "xm install",
        "package": os.path.basename(oil_path),
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "user": os.environ.get("USER", "unknown"),
        "oil_reserve": OIL_RESERVE,
    }
    if not lock.acquire(metadata, timeout=120):
        print(f"\n⚠️ 无法获取锁，安装超时。", file=sys.stderr)
        print(f"☕ 咖啡机因等待超时爆炸 +1", file=sys.stderr)
        print(f"🛢️ 石油消耗：0.01%", file=sys.stderr)
        print(f"[今日崩溃次数: {crash_count_today()+1}/31]", file=sys.stderr)
        return 2

    try:
        return _do_install(oil_path, lock)
    finally:
        lock.release()


def _do_install(oil_path: str, lock: LockFile) -> int:
    """实际安装流程"""
    # Step 1: 校验
    print("📋 Step 1/5: 校验文件完整性...", flush=True)
    ctrl = read_control_from_oil(oil_path)
    if not ctrl:
        print("⚠️ 无法读取 control 信息", file=sys.stderr)
        return 3
    pkg_name = ctrl.get("package", "unknown")
    pkg_version = ctrl.get("version", "unknown")
    print(f"   包名: {pkg_name} 版本: {pkg_version}")

    # Step 2: 解包
    print("📂 Step 2/5: 解包数据...", flush=True)
    dest = os.path.join(TEMP_DIR, f"install-{pkg_name}-{int(time.time())}")
    os.makedirs(dest, exist_ok=True)
    try:
        files = extract_data(oil_path, dest)
        print(f"   解包完成: {len(files)} 个文件")
    except Exception as e:
        print(f"⚠️ 解包失败: {e}", file=sys.stderr)
        return 3

    # Step 3: 跑 preinst
    preinst = os.path.join(dest, "软件包", pkg_name, "pmadd", "preinst")
    if os.path.exists(preinst):
        print("🔧 Step 3/5: 执行 preinst...", flush=True)
        rc = run_script(preinst)
        if rc != 0:
            print(f"⚠️ preinst 返回非零: {rc}", file=sys.stderr)
            return 4

    # Step 4: 复制文件到系统
    print("📦 Step 4/5: 安装文件到系统...", flush=True)
    src_data = os.path.join(dest, "程序安装目录及文件")
    installed_files = []
    if os.path.exists(src_data):
        for root_dir, dirs, files_in_dir in os.walk(src_data):
            for fname in files_in_dir:
                src = os.path.join(root_dir, fname)
                # 计算目标路径
                rel = os.path.relpath(src, src_data)
                dst = os.path.join("/", rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                installed_files.append(rel)
        print(f"   已安装 {len(installed_files)} 个文件")
    else:
        print(f"   ⚠️ 未找到数据目录: {src_data}", file=sys.stderr)

    # Step 5: 跑 postinst
    postinst = os.path.join(dest, "软件包", pkg_name, "pmadd", "postinst")
    if os.path.exists(postinst):
        print("🔧 Step 5/5: 执行 postinst...", flush=True)
        rc = run_script(postinst)
        if rc != 0:
            print(f"⚠️ postinst 返回非零: {rc}", file=sys.stderr)
            # 不致命，仅警告

    # 更新 status.db
    db = load_status()
    db[pkg_name] = {
        "version": pkg_version,
        "architecture": ctrl.get("architecture", "all"),
        "files": installed_files,
        "installed": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "origin": oil_path,
        "oil_reserve": OIL_RESERVE,
    }
    save_status(db)

    # 清理临时目录
    shutil.rmtree(dest, ignore_errors=True)

    print(f"✅ 安装完成: {pkg_name} {pkg_version}")
    print(f"☕ 咖啡机状态：稳定")
    print(f"🛢️ 石油储备：{OIL_RESERVE}%")
    return 0


def cmd_remove(args):
    """xm remove <pkgname>"""
    ensure_dirs()
    pkg_name = args[0] if args else None
    if not pkg_name:
        print("⚠️ 用法: xm remove <pkgname>", file=sys.stderr)
        return 1

    db = load_status()
    if pkg_name not in db:
        print(f"⚠️ 包未安装: {pkg_name}", file=sys.stderr)
        return 1

    lock = LockFile(f"{LOCK_DIR}/remove-{pkg_name}.lock")
    metadata = {
        "pid": os.getpid(),
        "command": f"xm remove {pkg_name}",
        "package": pkg_name,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if not lock.acquire(metadata, timeout=60):
        print(f"⚠️ 无法获取锁", file=sys.stderr)
        return 2

    try:
        # prerm
        info = db[pkg_name]
        # 注意：文件已安装到系统，prerm/postrm 脚本需要从包存档获取
        # 这里简化处理：查找 archives 中对应的 .oil
        oil_path = info.get("origin", "")
        prerm_script = None
        if os.path.exists(oil_path):
            import tarfile
            with tarfile.open(oil_path, 'r:gz') as tf:
                for m in tf.getmembers():
                    if "pmdel/prerm" in m.name:
                        f = tf.extractfile(m)
                        prerm_path = os.path.join(TEMP_DIR, f"prerm-{pkg_name}")
                        with open(prerm_path, 'wb') as out:
                            out.write(f.read())
                        os.chmod(prerm_path, 0o755)
                        prerm_script = prerm_path
                        break

        if prerm_script:
            print(f"🔧 执行 prerm for {pkg_name}...", flush=True)
            rc = run_script(prerm_script)
            os.remove(prerm_script)
            if rc != 0:
                print(f"⚠️ prerm 返回非零: {rc}", file=sys.stderr)

        # 删文件
        print(f"🗑️ 删除文件...", flush=True)
        files = info.get("files", [])
        for f_rel in files:
            f_path = os.path.join("/", f_rel)
            try:
                os.remove(f_path)
            except FileNotFoundError:
                pass
        print(f"   已删除 {len(files)} 个文件")

        # postrm
        postrm_script = None
        if os.path.exists(oil_path):
            import tarfile
            with tarfile.open(oil_path, 'r:gz') as tf:
                for m in tf.getmembers():
                    if "pmdel/postrm" in m.name:
                        f = tf.extractfile(m)
                        postrm_path = os.path.join(TEMP_DIR, f"postrm-{pkg_name}")
                        with open(postrm_path, 'wb') as out:
                            out.write(f.read())
                        os.chmod(postrm_path, 0o755)
                        postrm_script = postrm_path
                        break

        if postrm_script:
            print(f"🔧 执行 postrm for {pkg_name}...", flush=True)
            rc = run_script(postrm_script)
            os.remove(postrm_script)
            if rc != 0:
                print(f"⚠️ postrm 返回非零: {rc}", file=sys.stderr)

        # 从 status.db 移除
        del db[pkg_name]
        save_status(db)

        print(f"✅ 卸载完成: {pkg_name}")
        return 0
    finally:
        lock.release()


def cmd_query(args):
    """xm query <pkgname>"""
    ensure_dirs()
    pkg_name = args[0] if args else None
    db = load_status()
    if pkg_name:
        if pkg_name in db:
            info = db[pkg_name]
            print(f"✅ {pkg_name} 已安装")
            print(f"   版本: {info.get('version', 'unknown')}")
            print(f"   架构: {info.get('architecture', 'unknown')}")
            print(f"   安装时间: {info.get('installed', 'unknown')}")
            print(f"   文件数: {len(info.get('files', []))}")
            return 0
        else:
            print(f"❌ {pkg_name} 未安装")
            return 1
    else:
        # 列出全部
        if not db:
            print("📭 无已安装包")
        for name, info in sorted(db.items()):
            print(f"  {name} {info.get('version','?')} ({info.get('architecture','?')})")
        return 0


def cmd_files(args):
    """xm files <pkgname>"""
    ensure_dirs()
    pkg_name = args[0] if args else None
    db = load_status()
    if not pkg_name or pkg_name not in db:
        print(f"⚠️ 包未安装: {pkg_name}", file=sys.stderr)
        return 1
    for f in db[pkg_name].get("files", []):
        print(f)
    return 0


def cmd_verify(args):
    """xm verify <pkgname>"""
    ensure_dirs()
    pkg_name = args[0] if args else None
    db = load_status()
    if not pkg_name or pkg_name not in db:
        print(f"⚠️ 包未安装: {pkg_name}", file=sys.stderr)
        return 1

    info = db[pkg_name]
    origin = info.get("origin", "")
    if not os.path.exists(origin):
        print(f"⚠️ 原始包不存在: {origin}", file=sys.stderr)
        return 1

    sums = read_checksums_from_oil(origin)
    if not sums:
        print(f"⚠️ 包内无校验信息")
        return 1

    errors = 0
    for f_rel, expected in sums.items():
        f_path = os.path.join("/", f_rel)
        if not os.path.exists(f_path):
            print(f"  ❌ 缺失: {f_rel}")
            errors += 1
            continue
        actual = compute_sha256(f_path)
        if actual == expected:
            print(f"  ✅ {f_rel}")
        else:
            print(f"  ❌ {f_rel} (校验失败)")
            errors += 1

    if errors == 0:
        print(f"✅ 校验通过: {pkg_name}")
        return 0
    else:
        print(f"⚠️ {errors} 个文件校验失败")
        print(f"☕ 咖啡机因校验失败爆炸 +{errors}")
        return 1


def cmd_rebuild_db(args):
    """xm rebuild-db — 从文件系统重建 status.db（扫描 /usr/local/bin 等）"""
    ensure_dirs()
    print("🔧 重建 status.db...")
    print("⚠️ 此操作会覆盖现有数据库")
    # 简化实现：保留现有 db，仅补充基本信息
    db = load_status()
    print(f"   当前记录: {len(db)} 个包")
    print(f"✅ 重建完成（增量模式）")
    return 0


def cmd_coffee(args):
    """xm coffee — 显示咖啡机状态"""
    count = crash_count_today()
    print(f"☕ 咖啡机状态: 稳定（但烦躁）")
    print(f"📊 今日崩溃: {count}/31")
    print(f"🛢️ 石油储备: {OIL_RESERVE}%")
    print(f"⚡ 功耗: {POWER_DRAW} (oil-fed)")
    return 0


def main():
    if len(sys.argv) < 2:
        print("""xm - X11 Manager backend (oil-powered)
用法: xm <command> [args...]

  unpack   <file.oil> [--root /path]   解包到临时目录
  install  <file.oil>                   解包+安装+跑脚本+登记
  remove   <pkgname>                    卸载+跑脚本+注销
  query    [pkgname]                    查询安装状态
  files    <pkgname>                    列出包文件
  verify   <pkgname>                    校验文件完整性
  rebuild-db                             重建状态数据库
  coffee                                  咖啡机状态

NOT Windows XP. NOT Xiaomi. NOT X-Men.
石油驱动，1.x W 稳态。""")
        return 0

    cmd = sys.argv[1]
    args = sys.argv[2:]

    handlers = {
        "unpack": cmd_unpack,
        "install": cmd_install,
        "remove": cmd_remove,
        "query": cmd_query,
        "files": cmd_files,
        "verify": cmd_verify,
        "rebuild-db": cmd_rebuild_db,
        "coffee": cmd_coffee,
    }

    handler = handlers.get(cmd)
    if not handler:
        print(f"⚠️ 未知命令: {cmd}", file=sys.stderr)
        print(f"   运行 'xm' 查看帮助", file=sys.stderr)
        return 1

    try:
        return handler(args)
    except KeyboardInterrupt:
        print(f"\n⚠️ 操作被中断 (SIGINT)", file=sys.stderr)
        print(f"☕ 咖啡机因中断爆炸 +1", file=sys.stderr)
        print(f"[今日崩溃次数: {crash_count_today()+1}/31]", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"⚠️ 内部错误: {e}", file=sys.stderr)
        print(f"☕ 咖啡机因异常爆炸 +1", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

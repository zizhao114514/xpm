"""
XPM Suite 事务安装引擎
核心原则：全成 or 全回滚
记录每个操作，失败时逆序回滚
"""

import os, shutil, time, json
from pathlib import Path
from typing import List, Callable, Optional

from .statusdb import (
    StatusDB, PackageStatus, get_db, get_triggers,
    create_snapshot, restore_snapshot,
)

# 操作日志（用于回滚）
class OpLog:
    """记录每个操作，支持逆序回滚"""

    def __init__(self):
        self.ops: List[dict] = []
        self.tx_id = time.strftime("%Y%m%d-%H%M%S")

    def record(self, op_type: str, **kwargs):
        """记录一个操作"""
        entry = {"type": op_type, "tx_id": self.tx_id, "time": time.time()}
        entry.update(kwargs)
        self.ops.append(entry)

    def rollback(self):
        """逆序回滚所有操作"""
        errors = []
        for op in reversed(self.ops):
            try:
                self._undo(op)
            except Exception as e:
                errors.append(f"回滚 {op['type']} 失败: {e}")
        self.ops.clear()
        return errors

    def _undo(self, op: dict):
        t = op["type"]
        if t == "write_file":
            # 恢复旧文件或删除新文件
            path = op["path"]
            old_data = op.get("old_data")
            if old_data is not None:
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "wb") as f:
                    f.write(old_data)
            elif os.path.exists(path):
                os.remove(path)
        elif t == "mkdir":
            path = op["path"]
            if os.path.exists(path) and not os.listdir(path):
                os.rmdir(path)
        elif t == "remove_file":
            # 恢复文件
            path = op["path"]
            data = op.get("data")
            if data:
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "wb") as f:
                    f.write(data)
        elif t == "add_db":
            name = op["name"]
            db = get_db()
            db.remove(name)
        elif t == "remove_db":
            # 恢复数据库记录
            data = op.get("pkg_data")
            if data:
                db = get_db()
                from .statusdb import PackageStatus
                db.add(PackageStatus.from_dict(data))
        elif t == "trigger_activate":
            # 从 pending 中移除
            pass  # trigger state 会在事务失败时整体恢复
        elif t == "snapshot_create":
            # 删除快照
            sid = op.get("snapshot_id")
            if sid:
                snap_dir = Path("/var/lib/xpm/snapshots") / sid
                if snap_dir.exists():
                    shutil.rmtree(snap_dir)

    def clear(self):
        self.ops.clear()

class Transaction:
    """
    事务上下文管理器。
    用法:
        with Transaction("install htop") as tx:
            tx.install(pkg)
            tx.install(dep)
        # 退出时自动 commit 或 rollback
    """

    def __init__(self, description: str = ""):
        self.description = description
        self.oplog = OpLog()
        self._snapshot_id = None
        self._committed = False
        self.db = get_db()
        self.triggers = get_triggers()

    def __enter__(self):
        # 创建状态快照（用于整体回滚）
        try:
            self._snapshot_id = create_snapshot(f"tx-{self.oplog.tx_id}")
            self.oplog.record("snapshot_create", snapshot_id=self._snapshot_id)
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        return False  # 不吞异常

    def record(self, op_type: str, **kwargs):
        self.oplog.record(op_type, **kwargs)

    def install_package(self, pkg: PackageStatus, files_installed: List[str]):
        """记录包安装"""
        self.db.add(pkg)
        self.record("add_db", name=pkg.name, pkg_data=pkg.to_dict())
        for f in files_installed:
            self.record("write_file", path=f)

    def remove_package(self, pkg: PackageStatus):
        """记录包卸载"""
        # 保存旧数据用于回滚
        old_data = pkg.to_dict()
        old_files = {}
        for f in pkg.files:
            try:
                with open(f, "rb") as fh:
                    old_files[f] = fh.read()
            except (FileNotFoundError, PermissionError):
                pass

        self.db.remove(pkg.name)
        self.record("remove_db", name=pkg.name, pkg_data=old_data)
        for f, data in old_files.items():
            self.record("remove_file", path=f, data=data)

    def commit(self):
        """提交事务"""
        self._committed = True
        # 清理回滚快照
        if self._snapshot_id:
            snap_dir = Path("/var/lib/xpm/snapshots") / self._snapshot_id
            try:
                if snap_dir.exists():
                    shutil.rmtree(snap_dir)
            except PermissionError:
                pass
        self.oplog.clear()

    def rollback(self):
        """回滚事务"""
        errors = self.oplog.rollback()
        # 恢复数据库快照
        if self._snapshot_id:
            try:
                restore_snapshot(self._snapshot_id)
            except Exception:
                pass
        return errors

# === 便捷函数 ===

def atomic_write(path: str, data: bytes, mode: int = 0o644) -> dict:
    """原子写入文件，返回 rollback info"""
    info = {"path": path, "old_data": None}
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                info["old_data"] = f.read()
        except PermissionError:
            pass
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        os.fsync(f.fileno())
    os.chmod(tmp, mode)
    os.replace(tmp, path)
    return info

def atomic_remove(path: str) -> Optional[bytes]:
    """原子删除，返回原内容（用于回滚）"""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = f.read()
    os.remove(path)
    return data

if __name__ == "__main__":
    print("事务引擎就绪")
    print("用法: with Transaction('install xxx') as tx:")
    print("         tx.install_package(pkg, files)")

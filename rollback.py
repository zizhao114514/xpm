#!/usr/bin/env python3
"""
rollback.py - XPM 事务回滚
支持回滚到任意历史事务状态
"""

import os
import json
import tarfile
import shutil
import glob
from datetime import datetime

TRANSACTION_LOG = "/var/log/xpm/transactions.log"
ROLLBACK_DIR = "/var/cache/xpm/rollback"
STATUS_DB = "/var/lib/xpm/status.db"

class RollbackManager:
    """管理事务回滚"""

    def __init__(self, log_path=TRANSACTION_LOG, cache_dir=ROLLBACK_DIR):
        self.log_path = log_path
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log_transaction(self, tx_id, operation, packages, state="done"):
        """记录事务到日志"""
        entry = {
            "id": tx_id,
            "timestamp": datetime.now().isoformat(),
            "operation": operation,  # install/remove/upgrade
            "packages": packages,    # [{name, version, action}]
            "state": state,
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def list_transactions(self, limit=20):
        """列出最近的事务"""
        if not os.path.exists(self.log_path):
            return []
        txs = []
        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    txs.append(json.loads(line))
        return txs[-limit:][::-1]  # 最新的在前

    def save_snapshot(self, tx_id, files_before):
        """
        安装/卸载前保存受影响文件的快照
        files_before: {filepath: sha256_before}
        """
        snap_dir = os.path.join(self.cache_dir, tx_id)
        os.makedirs(snap_dir, exist_ok=True)

        manifest = {}
        for filepath, sha_before in files_before.items():
            if os.path.exists(filepath):
                # 保存文件内容
                dest = os.path.join(snap_dir, filepath.lstrip("/").replace("/", "_"))
                shutil.copy2(filepath, dest)
                manifest[filepath] = {
                    "backup": dest,
                    "sha256_before": sha_before,
                }
            else:
                manifest[filepath] = {
                    "backup": None,
                    "sha256_before": None,
                }

        with open(os.path.join(snap_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)

        return snap_dir

    def rollback_transaction(self, tx_id):
        """
        回滚指定事务
        返回 (success: bool, message: str)
        """
        snap_dir = os.path.join(self.cache_dir, tx_id)
        manifest_path = os.path.join(snap_dir, "manifest.json")

        if not os.path.exists(manifest_path):
            return False, f"找不到事务 {tx_id} 的快照"

        with open(manifest_path) as f:
            manifest = json.load(f)

        restored = 0
        failed = 0
        for filepath, info in manifest.items():
            backup = info.get("backup")
            if backup and os.path.exists(backup):
                try:
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    shutil.copy2(backup, filepath)
                    restored += 1
                except Exception as e:
                    failed += 1
            elif info.get("sha256_before") is None:
                # 文件之前不存在，需要删除
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        restored += 1
                    except:
                        failed += 1

        # 更新状态数据库
        self._update_status_after_rollback(tx_id)

        # 标记事务为已回滚
        self._mark_rolled_back(tx_id)

        return True, f"回滚完成: 恢复 {restored} 个文件, 失败 {failed} 个"

    def _update_status_after_rollback(self, tx_id):
        """回滚后更新 status.db（简化版）"""
        # 读取事务日志找到对应的包操作
        # 反向操作：install → remove, remove → install
        pass  # 由调用者处理

    def _mark_rolled_back(self, tx_id):
        """在日志中标记事务已回滚"""
        if not os.path.exists(self.log_path):
            return
        lines = open(self.log_path).readlines()
        new_lines = []
        for line in lines:
            if tx_id in line and '"state": "done"' in line:
                line = line.replace('"state": "done"', '"state": "rolled_back"')
            new_lines.append(line)
        with open(self.log_path, "w") as f:
            f.writelines(new_lines)

    def rollback_to(self, tx_index):
        """
        回滚到指定事务之前的状态
        tx_index: 事务 ID 或序号（从 1 开始，最新为 1）
        """
        txs = self.list_transactions(limit=100)
        if not txs:
            return False, "没有可回滚的事务"

        target = None
        if isinstance(tx_index, int) or tx_index.isdigit():
            idx = int(tx_index)
            if 1 <= idx <= len(txs):
                target = txs[idx - 1]
        else:
            for tx in txs:
                if tx["id"] == tx_index:
                    target = tx
                    break

        if not target:
            return False, f"找不到事务: {tx_index}"

        return self.rollback_transaction(target["id"])

    def auto_rollback_on_failure(self, tx_id):
        """
        安装/卸载失败时的自动回滚
        由 xm 后端在捕获异常时调用
        """
        snap_dir = os.path.join(self.cache_dir, tx_id)
        if not os.path.exists(snap_dir):
            return False, "无快照可回滚"

        result = self.rollback_transaction(tx_id)
        if result[0]:
            return True, f"自动回滚成功: {result[1]}"
        return result


def generate_tx_id(operation, packages):
    """生成事务 ID"""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    pkg_short = "_".join(p["name"] for p in packages[:3])
    if len(packages) > 3:
        pkg_short += f"_+{len(packages)-3}"
    return f"{operation}-{ts}-{pkg_short}"


if __name__ == "__main__":
    rb = RollbackManager()

    # 测试
    tx_id = generate_tx_id("install", [{"name": "vim"}])
    print(f"测试事务 ID: {tx_id}")

    rb.log_transaction(tx_id, "install", [{"name": "vim", "version": "2:9.0"}])

    txs = rb.list_transactions()
    print(f"最近事务: {len(txs)} 条")
    for t in txs:
        print(f"  {t['id']}  {t['operation']}  {t['state']}")

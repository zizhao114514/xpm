"""
XPM Suite 触发器引擎
纯 Python 实现，不依赖 dpkg --triggers-only
支持: interest / activate / file-trigger / explicit
"""

import os, stat as stat_mod, time
from typing import List, Dict, Optional, Callable

from .statusdb import get_triggers, get_db, TriggerState
from .transaction import Transaction

# 触发器处理优先级
TRIGGER_PRIORITIES = {
    "glibc-update": 100,    # 最高优先级
    "fontconfig-rebuild": 80,
    "man-db-update": 60,
    "initramfs-update": 90,
    "ldconfig": 95,
    "shared-mime-info": 50,
    "desktop-database": 40,
    "gtk-update-icon-cache": 30,
    "gdk-pixbuf-query-loaders": 25,
    "pango-querymodules": 20,
}

# 内置触发器处理器（无需 maintainer script）
BUILTIN_HANDLERS = {
    "ldconfig": lambda: os.system("ldconfig 2>/dev/null") == 0,
    "man-db-update": lambda: os.system("mandb 2>/dev/null") == 0,
    "fontconfig-rebuild": lambda: os.system("fc-cache -f 2>/dev/null") == 0,
    "shared-mime-info": lambda: os.system("update-mime-database /usr/share/mime 2>/dev/null") == 0,
    "desktop-database": lambda: os.system("update-desktop-database 2>/dev/null") == 0,
}

class TriggerEngine:
    """触发器引擎"""

    def __init__(self):
        self.ts: TriggerState = get_triggers()
        self.db = get_db()
        self._handlers: Dict[str, Callable] = dict(BUILTIN_HANDLERS)
        self._pending_processed = []

    def register_handler(self, name: str, handler: Callable):
        """注册自定义触发器处理器"""
        self._handlers[name] = handler

    def register_interest(self, trigger_name: str, package: str):
        """包声明对触发器感兴趣"""
        self.ts.register_interest(trigger_name, package)

    def register_package_triggers(self, pkg_name: str, trigger_fields: dict):
        """
        从包的 control 字段注册触发器。
        trigger_fields:
            - Triggers-Pending: trigger1,trigger2
            - Interest: trigger1,trigger2
            - Activate: trigger1
        """
        # 注册 interest（我关心这些）
        interest = trigger_fields.get("Interest", "")
        for t in [x.strip() for x in interest.split(",") if x.strip()]:
            self.register_interest(t, pkg_name)

        # 注册 activate（我激活这些）
        activate = trigger_fields.get("Activate", "")
        for t in [x.strip() for x in activate.split(",") if x.strip()]:
            self.activate(t, pkg_name)

        # Triggers-Pending（我需要被触发）
        pending = trigger_fields.get("Triggers-Pending", "")
        for t in [x.strip() for x in pending.split(",") if x.strip()]:
            self.register_interest(t, pkg_name)

    def activate(self, trigger_name: str, by_package: str):
        """激活一个触发器"""
        self.ts.activate(trigger_name, by_package)

    def activate_for_files(self, file_paths: List[str]):
        """
        根据安装的文件路径自动激活 file-trigger。
        例如：安装了 /usr/share/fonts/xxx → 激活 fontconfig-rebuild
        """
        path_rules = [
            ("/usr/share/fonts/", "fontconfig-rebuild"),
            ("/usr/share/man/", "man-db-update"),
            ("/usr/lib/", "ldconfig"),
            ("/etc/ld.so.conf", "ldconfig"),
            ("/usr/share/mime/", "shared-mime-info"),
            ("/usr/share/applications/", "desktop-database"),
            ("/usr/share/icons/", "gtk-update-icon-cache"),
        ]
        activated = set()
        for fp in file_paths:
            for path_prefix, trigger in path_rules:
                if fp.startswith(path_prefix):
                    if trigger not in activated:
                        self.activate(trigger, "auto")
                        activated.add(trigger)
                    break

    def process_pending(self, tx: Optional[Transaction] = None) -> dict:
        """
        处理所有 pending 触发器。
        按优先级排序，逐个执行。
        返回 {trigger: (success: bool, output: str)}
        """
        pending = self.ts.get_pending()
        if not pending:
            return {}

        # 按优先级排序
        sorted_triggers = sorted(
            pending.items(),
            key=lambda x: TRIGGER_PRIORITIES.get(x[0], 0),
            reverse=True
        )

        results = {}
        for trigger_name, activators in sorted_triggers:
            result = self._execute_trigger(trigger_name, activators, tx)
            results[trigger_name] = result
            if not result[0]:
                # 失败时记录但继续处理其他触发器
                pass

        # 清除已处理的 pending
        for trigger_name in pending:
            self.ts.clear_pending(trigger_name)

        return results

    def _execute_trigger(self, name: str, activators: List[str],
                         tx: Optional[Transaction]) -> tuple:
        """执行单个触发器"""
        # 方法1: 内置处理器
        if name in self._handlers:
            try:
                ok = self._handlers[name]()
                return (bool(ok), "builtin handler")
            except Exception as e:
                return (False, str(e))

        # 方法2: 调用 interested 包的 postinst trigger <name>
        interested = self.ts.interested_packages(name)
        results = []
        for pkg_name in interested:
            pkg = self.db.get(pkg_name)
            if not pkg:
                continue
            # 查找 postinst 脚本
            script_path = f"/var/lib/dpkg/info/{pkg_name}.postinst"
            if not os.path.exists(script_path):
                # 尝试 XPM 管理的路径
                script_path = f"/var/lib/xpm/info/{pkg_name}.postinst"
            if os.path.exists(script_path):
                import subprocess
                try:
                    r = subprocess.run(
                        [script_path, "triggered", name],
                        capture_output=True, text=True, timeout=60
                    )
                    results.append(r.returncode == 0)
                except Exception as e:
                    results.append(False)
            else:
                results.append(True)  # 没有脚本就不算失败

        success = all(results) if results else True
        return (success, f"notified {len(interested)} packages")

    def get_status(self) -> dict:
        """获取触发器状态摘要"""
        pending = self.ts.get_pending()
        interests = self.ts._data.get("interests", {})
        return {
            "pending_count": sum(len(v) for v in pending.values()),
            "pending_triggers": list(pending.keys()),
            "registered_interests": len(interests),
            "total_interest_rules": sum(len(v) for v in interests.values()),
        }

    def snapshot(self) -> dict:
        return self.ts.snapshot()

    def restore(self, snap: dict):
        self.ts.restore(snap)

# === 便捷函数 ===

_engine_instance = None

def get_engine() -> TriggerEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = TriggerEngine()
    return _engine_instance

def process_all_triggers(tx: Optional[Transaction] = None) -> dict:
    """处理所有 pending 触发器"""
    return get_engine().process_pending(tx)

if __name__ == "__main__":
    eng = get_engine()
    status = eng.get_status()
    print(f"触发器状态: {json.dumps(status, indent=2)}")
    results = eng.process_pending()
    if results:
        print(f"处理结果:")
        for name, (ok, msg) in results.items():
            icon = "✅" if ok else "❌"
            print(f"  {icon} {name}: {msg}")
    else:
        print("没有 pending 触发器")

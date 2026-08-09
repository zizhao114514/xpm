"""
XPM Suite 状态数据库
替代 /var/lib/dpkg/status，纯 JSON 实现
记录已安装包、版本、架构、文件清单、触发���状态
"""

import json, os, time
from pathlib import Path
from typing import Dict, List, Optional

STATE_DIR = Path("/var/lib/xpm")
STATUS_FILE = STATE_DIR / "status.json"
FILES_DIR = STATE_DIR / "info"  # 每个包一个 .list 文件
TRIGGERS_FILE = STATE_DIR / "triggers.json"
SNAPSHOTS_DIR = STATE_DIR / "snapshots"

def ensure_dirs():
    for d in [STATE_DIR, FILES_DIR, SNAPSHOTS_DIR]:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            pass

class PackageStatus:
    """单个包的状态记录"""
    def __init__(self, name, version, arch, source_format="deb",
                 files=None, depends=None, installed_by="xpm",
                 install_time=None, triggers=None, locked=False):
        self.name = name
        self.version = version
        self.arch = arch
        self.source_format = source_format  # "deb" or "oil"
        self.files = files or []
        self.depends = depends or []
        self.installed_by = installed_by
        self.install_time = install_time or time.time()
        self.triggers = triggers or {"interest": [], "activate": []}
        self.locked = locked
        self.state = "installed"  # installed / half-installed / failed

    def to_dict(self):
        return {
            "name": self.name, "version": self.version, "arch": self.arch,
            "source_format": self.source_format, "files": self.files,
            "depends": self.depends, "installed_by": self.installed_by,
            "install_time": self.install_time, "triggers": self.triggers,
            "locked": self.locked, "state": self.state,
        }

    @classmethod
    def from_dict(cls, d):
        p = cls(**{k: v for k, v in d.items()
                   if k in cls.__init__.__code__.co_varnames})
        # 额外字段
        p.state = d.get("state", "installed")
        return p

class StatusDB:
    """状态数据库（单例模式）"""

    def __init__(self):
        ensure_dirs()
        self._packages: Dict[str, PackageStatus] = {}
        self._load()

    def _load(self):
        try:
            with open(STATUS_FILE) as f:
                data = json.load(f)
            for name, pd in data.items():
                self._packages[name] = PackageStatus.from_dict(pd)
        except (FileNotFoundError, json.JSONDecodeError):
            self._packages = {}

    def _save(self):
        try:
            ensure_dirs()
            tmp = STATUS_FILE.with_suffix(".json.tmp")
            with open(tmp, "w") as f:
                json.dump({n: p.to_dict() for n, p in self._packages.items()},
                          f, indent=2)
            os.replace(tmp, STATUS_FILE)
        except PermissionError:
            pass

    # === 查询 ===

    def is_installed(self, name) -> bool:
        return name in self._packages and self._packages[name].state == "installed"

    def get(self, name) -> Optional[PackageStatus]:
        return self._packages.get(name)

    def all_packages(self) -> List[PackageStatus]:
        return list(self._packages.values())

    def installed_packages(self) -> List[PackageStatus]:
        return [p for p in self._packages.values() if p.state == "installed"]

    def search(self, keyword: str) -> List[PackageStatus]:
        kw = keyword.lower()
        return [p for p in self._packages.values()
                if kw in p.name.lower() or kw in p.version.lower()]

    def get_files(self, name) -> List[str]:
        p = self._packages.get(name)
        return p.files if p else []

    # === 修改 ===

    def add(self, pkg: PackageStatus):
        self._packages[pkg.name] = pkg
        self._save()
        # 写文件清单
        self._write_file_list(pkg)

    def remove(self, name):
        if name in self._packages:
            del self._packages[name]
            self._save()
        # 删除文件清单
        fl = FILES_DIR / f"{name}.list"
        try:
            fl.unlink()
        except FileNotFoundError:
            pass

    def set_state(self, name, state):
        if name in self._packages:
            self._packages[name].state = state
            self._save()

    def lock(self, name):
        if name in self._packages:
            self._packages[name].locked = True
            self._save()

    def unlock(self, name):
        if name in self._packages:
            self._packages[name].locked = False
            self._save()

    def is_locked(self, name) -> bool:
        p = self._packages.get(name)
        return p.locked if p else False

    def _write_file_list(self, pkg):
        ensure_dirs()
        fl = FILES_DIR / f"{pkg.name}.list"
        try:
            with open(fl, "w") as f:
                for fp in pkg.files:
                    f.write(fp + "\n")
        except PermissionError:
            pass

    # === 统计 ===

    def count(self) -> int:
        return len(self.installed_packages())

    def total_size_estimate(self) -> int:
        """粗略估算（文件数 × 平均大小）"""
        total = 0
        for p in self.installed_packages():
            total += len(p.files) * 4096  # 粗估
        return total

    def top_by_files(self, n=10) -> List[tuple]:
        pkgs = self.installed_packages()
        pkgs.sort(key=lambda p: len(p.files), reverse=True)
        return [(p.name, len(p.files), p.version) for p in pkgs[:n]]

# === 触发器状态管理 ===

class TriggerState:
    """管理触发器注册和 pending 状态"""

    def __init__(self):
        ensure_dirs()
        self._data = {"interests": {}, "pending": {}, "processed": {}}
        self._load()

    def _load(self):
        try:
            with open(TRIGGERS_FILE) as f:
                self._data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._data = {"interests": {}, "pending": {}, "processed": {}}

    def _save(self):
        try:
            ensure_dirs()
            tmp = TRIGGERS_FILE.with_suffix(".json.tmp")
            with open(tmp, "w") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp, TRIGGERS_FILE)
        except PermissionError:
            pass

    def register_interest(self, trigger_name: str, package: str):
        """包声明对某个触发器感兴趣"""
        if trigger_name not in self._data["interests"]:
            self._data["interests"][trigger_name] = []
        if package not in self._data["interests"][trigger_name]:
            self._data["interests"][trigger_name].append(package)
        self._save()

    def activate(self, trigger_name: str, by_package: str):
        """某个包激活了触发器"""
        if trigger_name not in self._data["pending"]:
            self._data["pending"][trigger_name] = []
        if by_package not in self._data["pending"][trigger_name]:
            self._data["pending"][trigger_name].append(by_package)
        self._save()

    def get_pending(self) -> Dict[str, List[str]]:
        return {k: v for k, v in self._data["pending"].items() if v}

    def clear_pending(self, trigger_name: str):
        self._data["pending"].pop(trigger_name, None)
        self._save()

    def interested_packages(self, trigger_name: str) -> List[str]:
        return self._data["interests"].get(trigger_name, [])

    def snapshot(self) -> dict:
        """返回当前完整状态（用于回滚）"""
        return json.loads(json.dumps(self._data))

    def restore(self, snapshot: dict):
        self._data = json.loads(json.dumps(snapshot))
        self._save()

# === 快照管理 ===

def create_snapshot(tag: str = "") -> str:
    """创建当前状态快照"""
    ensure_dirs()
    ts = time.strftime("%Y%m%d-%H%M%S")
    sid = f"{ts}-{tag}" if tag else ts
    snap_dir = SNAPSHOTS_DIR / sid
    snap_dir.mkdir(parents=True, exist_ok=True)

    # 复制 status
    try:
        import shutil
        shutil.copy2(STATUS_FILE, snap_dir / "status.json")
        shutil.copy2(TRIGGERS_FILE, snap_dir / "triggers.json")
    except (FileNotFoundError, PermissionError):
        pass

    # 写元数据
    meta = {
        "id": sid, "tag": tag, "time": time.time(),
        "packages": StatusDB().count(),
    }
    with open(snap_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    return sid

def list_snapshots() -> List[dict]:
    ensure_dirs()
    snaps = []
    for d in sorted(SNAPSHOTS_DIR.iterdir()):
        if d.is_dir():
            try:
                with open(d / "meta.json") as f:
                    snaps.append(json.load(f))
            except FileNotFoundError:
                snaps.append({"id": d.name, "tag": "", "time": 0, "packages": 0})
    return snaps

def restore_snapshot(sid: str) -> bool:
    """恢复到指定快照"""
    snap_dir = SNAPSHOTS_DIR / sid
    if not snap_dir.is_dir():
        return False
    try:
        import shutil
        shutil.copy2(snap_dir / "status.json", STATUS_FILE)
        shutil.copy2(snap_dir / "triggers.json", TRIGGERS_FILE)
        return True
    except PermissionError:
        return False

# === 单例 ===

_db_instance: Optional[StatusDB] = None
_trigger_instance: Optional[TriggerState] = None

def get_db() -> StatusDB:
    global _db_instance
    if _db_instance is None:
        _db_instance = StatusDB()
    return _db_instance

def get_triggers() -> TriggerState:
    global _trigger_instance
    if _trigger_instance is None:
        _trigger_instance = TriggerState()
    return _trigger_instance

if __name__ == "__main__":
    db = get_db()
    print(f"已安装包: {db.count()}")
    for p in db.installed_packages()[:10]:
        print(f"  {p.name:<30} {p.version:<15} {p.arch:<8} [{p.source_format}]")
    ts = get_triggers()
    pending = ts.get_pending()
    if pending:
        print(f"\nPending 触发器: {pending}")

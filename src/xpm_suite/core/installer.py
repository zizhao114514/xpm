"""
XPM Suite 核心安装引擎
串联: 下载 → 校验 → 解析 → 事务 → 安装 → 触发器
支持 .deb 和 .oil 两种格式
"""

import os, sys, shutil, hashlib, time, json
from typing import List, Optional, Tuple, Callable

from .config import get_arch, load_config, get_downloader_config
from .statusdb import StatusDB, PackageStatus, get_db
from .transaction import Transaction, atomic_write, atomic_remove
from .triggers import TriggerEngine, get_engine as get_trigger_engine
from .downloader import get_downloader, get_mirror_manager
from . import scripts_env
from .sources import load_all_sources, get_arch_for_source, validate_sources
from ..formats.deb import DebPackage, parse_deb_file, _split_depends
from ..formats.oil import OilPackage, parse_package

# === 进度回调类型 ===
ProgressCb = Callable[[int, int, str], None]

class InstallError(Exception):
    """安装失败"""
    pass

class DependencyError(Exception):
    """依赖解析失败"""
    pass

# === 依赖解析 ===

class DependencyResolver:
    """轻量依赖解析器"""

    def __init__(self, source_index: dict):
        """
        source_index: {pkg_name: {version: {...control fields...}}}
        """
        self.index = source_index
        self.db = get_db()

    def resolve(self, package_name: str, arch: str = None) -> List[str]:
        """
        解析依赖，返回安装顺序（被依赖的在前）。
        简化版：不支持版本约束的复杂 SAT，支持基本的 Depends 和 | 或关系。
        """
        if arch is None:
            arch = get_arch()

        visited = set()
        order = []

        def visit(name, stack=None):
            if stack is None:
                stack = []
            if name in visited:
                return
            if name in stack:
                raise DependencyError(f"循环依赖: {' → '.join(stack + [name])}")

            # 查索引
            if name not in self.index:
                # 可能已安装
                if self.db.is_installed(name):
                    visited.add(name)
                    return
                raise DependencyError(f"找不到包: {name}")

            stack.append(name)
            pkg_info = self.index[name]

            # 取最新版本
            versions = list(pkg_info.keys())
            if not versions:
                stack.pop()
                return
            # 简单取第一个（索引里通常只有一个）
            info = pkg_info[versions[0]]

            # 解析 depends
            depends_str = info.get("Depends", "")
            if depends_str:
                parts = self._split_top(depends_str)
                for alternatives in parts:
                    installed_any = False
                    for alt in alternatives:
                        alt_name = alt.split()[0].strip()
                        alt_name = alt_name.split(":")[0].strip()
                        if self.db.is_installed(alt_name):
                            installed_any = True
                            break
                    if not installed_any:
                        # 选第一个可安装的
                        for alt in alternatives:
                            alt_name = alt.split()[0].strip()
                            alt_name = alt_name.split(":")[0].strip()
                            if alt_name in self.index:
                                visit(alt_name, stack)
                                installed_any = True
                                break
                        if not installed_any:
                            # 如果所有 alternatives 都不在索引，可能是虚拟包
                            pass

            stack.pop()
            visited.add(name)
            order.append(name)

        visit(package_name)
        return order

    def _split_top(self, field: str) -> List[List[str]]:
        """顶层按逗号分，保留 | 组"""
        parts = []
        current = ""
        paren = 0
        for ch in field:
            if ch == "(":
                paren += 1
                current += ch
            elif ch == ")":
                paren -= 1
                current += ch
            elif ch == "," and paren == 0:
                if current.strip():
                    parts.append([current.strip()])
                current = ""
            else:
                current += ch
        if current.strip():
            parts.append([current.strip()])
        # 每个 part 再按 | 分
        result = []
        for p in parts:
            alternatives = []
            for item in p[0].split("|"):
                alternatives.append(item.strip())
            result.append(alternatives)
        return result

# === 索引管理 ===

class SourceIndex:
    """软件源索引"""

    def __init__(self):
        self.packages: dict = {}  # name -> {version -> info}
        self._arch = get_arch()
        self._sources = []

    def load_sources(self):
        """从 /etc/xpm/sources.list.d/ 加载源（使用 sources.py 模块）"""
        from .sources import load_all_sources
        self._sources = load_all_sources()
        return self._sources

    def update(self, progress_cb: Optional[ProgressCb] = None):
        """
        更新索引：下载 Packages.gz 并解析。
        每条源可指定 [arch=xxx] 覆盖默认架构。
        """
        self.load_sources()
        self.packages.clear()

        dl = get_downloader()
        default_arch = self._arch

        total = len(self._sources)
        for i, entry in enumerate(self._sources):
            label = entry.to_line() if hasattr(entry, 'to_line') else str(entry)
            if progress_cb:
                progress_cb(i, total, label)

            # 支持新旧两种格式（SourceEntry 对象 或 旧式字符串）
            if hasattr(entry, 'arch'):
                arch = entry.arch or default_arch
                url = entry.url.rstrip("/")
                suite = entry.suite
                comps = entry.components
            else:
                # 旧式字符串回退
                parsed = self._parse_source_line(entry)
                if not parsed:
                    continue
                suite, comps, options = parsed
                arch = options.get("arch", default_arch)
                url = ""

            for comp in comps:
                url_path = f"dists/{suite}/{comp}/binary-{arch}/Packages.gz"
                try:
                    tmp = f"/var/cache/xpm/Packages-{comp}-{arch}.gz"
                    os.makedirs("/var/cache/xpm", exist_ok=True)
                    dl.download_with_failover(url_path, tmp)
                    self._parse_packages_file(tmp, arch)
                except Exception as e:
                    print(f"  ⚠️ 索引更新失败 [{comp}/{arch}]: {e}")

        if progress_cb:
            progress_cb(total, total, "完成")

    def _parse_source_line(self, line: str) -> Optional[tuple]:
        """
        解析 deb [options] url suite comp1 comp2
        支持 Debian 标准方括号语法: deb [arch=arm64] https://mirror suite main
        也支持旧式空格分隔: deb https://mirror suite main arch=arm64
        """
        parts = line.split()
        if len(parts) < 4:
            return None

        # 处理 [arch=arm64 lang=en_US] 方括号选项块
        options = {}
        idx = 1  # 默认 url 在第 1 位
        if parts[1].startswith("[") and not parts[1].startswith("http"):
            # 找到闭合的 ]
            opt_str = ""
            j = 1
            while j < len(parts) and "]" not in parts[j]:
                opt_str += parts[j] + " "
                j += 1
            if j < len(parts):
                opt_str += parts[j]  # 包含 ]
            opt_str = opt_str.strip("[]").strip()
            for kv in opt_str.split():
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    options[k.strip()] = v.strip()
            idx = j + 1  # url 在 ] 之后

        if idx + 1 >= len(parts):
            return None

        url = parts[idx]
        suite = parts[idx + 1]
        comps = parts[idx + 2:]

        # 也处理尾部遗留的 arch= 写法
        filtered_comps = []
        for c in comps:
            if c.startswith("arch="):
                options.setdefault("arch", c.split("=")[1])
            else:
                filtered_comps.append(c)

        return (suite, filtered_comps, options)

    def _parse_packages_file(self, path: str, arch: str):
        """解析 Packages.gz 内容"""
        import gzip
        try:
            with gzip.open(path, "rt") as f:
                content = f.read()
        except Exception:
            # 可能没压缩
            with open(path, "r") as f:
                content = f.read()

        current = {}
        for line in content.splitlines():
            if not line.strip():
                if current.get("Package"):
                    name = current["Package"]
                    ver = current.get("Version", "0")
                    # 只保留匹配架构的
                    pkg_arch = current.get("Architecture", "all")
                    if pkg_arch in (arch, "all"):
                        if name not in self.packages:
                            self.packages[name] = {}
                        self.packages[name][ver] = dict(current)
                current = {}
            elif line.startswith((" ", "\t")):
                continue  # 续行忽略（简化处理）
            elif ":" in line:
                key, _, val = line.partition(":")
                current[key.strip()] = val.strip()

        # 最后一个包
        if current.get("Package"):
            name = current["Package"]
            ver = current.get("Version", "0")
            pkg_arch = current.get("Architecture", "all")
            if pkg_arch in (arch, "all"):
                if name not in self.packages:
                    self.packages[name] = {}
                self.packages[name][ver] = dict(current)

    def search(self, keyword: str, limit: int = 20) -> List[dict]:
        kw = keyword.lower()
        results = []
        for name, versions in self.packages.items():
            if kw in name.lower():
                # 取最新版本
                ver = sorted(versions.keys())[-1]
                info = versions[ver]
                results.append({
                    "name": name,
                    "version": ver,
                    "description": info.get("Description", "").split("\n")[0],
                    "section": info.get("Section", ""),
                    "size": info.get("Size", "0"),
                })
                if len(results) >= limit:
                    break
        return results

    def get_info(self, name: str) -> Optional[dict]:
        if name not in self.packages:
            return None
        ver = sorted(self.packages[name].keys())[-1]
        return self.packages[name][ver]

# === 安装引擎 ===

class InstallEngine:
    """核心安装引擎"""

    def __init__(self):
        self.db = get_db()
        self.triggers = get_trigger_engine()
        self.index = SourceIndex()
        self._downloader = get_downloader()

    def update_index(self, progress_cb=None):
        self.index.update(progress_cb)

    def search(self, keyword: str) -> List[dict]:
        return self.index.search(keyword)

    def install(self, package_name: str,
                progress_cb: Optional[ProgressCb] = None) -> bool:
        """
        安装一个包（含依赖）。
        使用事务保证原子性。
        """
        arch = get_arch()

        # 检查是否已安装
        if self.db.is_installed(package_name):
            print(f"  ℹ️ {package_name} 已安装")
            return True

        # 确保索引存在
        if not self.index.packages:
            print("  📥 索引为空，先更新...")
            self.update_index()

        # 解析依赖
        resolver = DependencyResolver(self.index.packages)
        try:
            order = resolver.resolve(package_name, arch)
        except DependencyError as e:
            print(f"  ❌ 依赖解析失败: {e}")
            return False

        # 过滤已安装的
        to_install = [n for n in order if not self.db.is_installed(n)]
        if not to_install:
            print(f"  ℹ️ {package_name} 的所有依赖已满足")
            return True

        print(f"  📦 将安装 {len(to_install)} 个包: {', '.join(to_install)}")

        # 事务安装
        with Transaction(f"install {package_name}") as tx:
            for pkg_name in to_install:
                self._install_one(pkg_name, tx, progress_cb)
            # 处理触发器
            trigger_results = self.triggers.process_pending(tx)
            for tname, (ok, msg) in trigger_results.items():
                icon = "✅" if ok else "⚠️"
                print(f"  {icon} 触发器 {tname}: {msg}")

        print(f"  ✅ {package_name} 安装完成")
        return True

    def _install_one(self, pkg_name: str, tx: Transaction,
                      progress_cb: Optional[ProgressCb] = None):
        """安装单个包"""
        # 获取包信息
        info = self.index.get_info(pkg_name)
        if not info:
            raise InstallError(f"索引中找不到: {pkg_name}")

        filename = info.get("Filename", "")
        sha256 = info.get("SHA256", "")
        version = info.get("Version", "")
        pkg_arch = info.get("Architecture", get_arch())

        # 下载
        cache_path = f"/var/cache/xpm/{os.path.basename(filename)}"
        os.makedirs("/var/cache/xpm", exist_ok=True)

        if progress_cb:
            progress_cb(0, 100, f"下载 {pkg_name}")

        self._downloader.download_with_failover(filename, cache_path, sha256)

        if progress_cb:
            progress_cb(50, 100, f"安装 {pkg_name}")

        # 解析包
        pkg_obj, fmt = parse_package(cache_path)

        # 校验
        ok, msg = pkg_obj.verify()
        if not ok:
            raise InstallError(f"包校验失败 [{pkg_name}]: {msg}")

        # 架构检查
        if pkg_obj.arch != "all" and pkg_obj.arch != get_arch():
            raise InstallError(
                f"架构不匹配: 包是 {pkg_obj.arch}，本机是 {get_arch()}")

        # 提取 maintainer scripts
        scripts_dir = f"/var/lib/xpm/info"
        os.makedirs(scripts_dir, exist_ok=True)
        for s in ["preinst", "postinst", "prerm", "postrm"]:
            script_path = f"{scripts_dir}/{pkg_name}.{s}"
            if hasattr(pkg_obj, 'extract_script'):
                pkg_obj.extract_script(s, script_path)
            elif hasattr(pkg_obj, 'extract_control_script'):
                pkg_obj.extract_control_script(s, script_path)

        # 运行 preinst
        preinst_path = f"{scripts_dir}/{pkg_name}.preinst"
        if os.path.exists(preinst_path):
            rc, out, err = scripts_env.run_script(
                preinst_path, pkg_name, version, pkg_arch, "preinst"
            )
            if rc != 0:
                raise InstallError(f"preinst 失败 [{pkg_name}]: {err}")

        # 解压文件
        installed_files = pkg_obj.extract_data("/", progress_cb=None)

        # 注册触发器
        trigger_fields = {}
        if hasattr(pkg_obj, 'triggers'):
            trigs = pkg_obj.triggers
            if isinstance(trigs, dict):
                for k, v in trigs.items():
                    if isinstance(v, list):
                        trigger_fields[k.capitalize()] = ",".join(v)
                    else:
                        trigger_fields[k.capitalize()] = str(v)

        # 也检查 control 字段
        control = getattr(pkg_obj, 'control', {})
        for tf in ["Triggers-Pending", "Interest", "Activate"]:
            if tf in control:
                trigger_fields[tf] = control[tf]

        if trigger_fields:
            self.triggers.register_package_triggers(pkg_name, trigger_fields)

        # 根据安装的文件路径自动激活 file-trigger
        self.triggers.activate_for_files(installed_files)

        # 运行 postinst
        postinst_path = f"{scripts_dir}/{pkg_name}.postinst"
        if os.path.exists(postinst_path):
            rc, out, err = scripts_env.run_script_with_args(
                postinst_path, ["configure"], pkg_name, version, pkg_arch,
                "postinst"
            )
            if rc != 0:
                # postinst 失败不致命，记录警告
                print(f"  ⚠️ postinst 警告 [{pkg_name}]: {err}")

        # 写入数据库
        pkg_status = PackageStatus(
            name=pkg_name,
            version=version,
            arch=pkg_arch,
            source_format=fmt,
            files=installed_files,
            depends=info.get("Depends", "").split(","),
            installed_by="xpm",
        )
        tx.install_package(pkg_status, installed_files)

        if progress_cb:
            progress_cb(100, 100, f"完成 {pkg_name}")

    def remove(self, package_name: str,
               purge: bool = False,
               progress_cb: Optional[ProgressCb] = None) -> bool:
        """卸载包"""
        pkg = self.db.get(package_name)
        if not pkg or pkg.state != "installed":
            print(f"  ⚠️ {package_name} 未安装")
            return False

        if pkg.locked:
            print(f"  🔒 {package_name} 已锁定，先解锁: xpm unlock {package_name}")
            return False

        # 检查是否被其他包依赖
        for other in self.db.installed_packages():
            if other.name == package_name:
                continue
            for dep in other.depends:
                dep_name = dep.split()[0].strip() if dep else ""
                if dep_name == package_name:
                    print(f"  ⚠️ {package_name} 被 {other.name} 依赖")
                    return False

        with Transaction(f"remove {package_name}") as tx:
            # 运行 prerm
            scripts_dir = f"/var/lib/xpm/info"
            prerm = f"{scripts_dir}/{package_name}.prerm"
            if os.path.exists(prerm):
                scripts_env.run_script(prerm, package_name, pkg.version, pkg.arch, "prerm")

            # 删除文件
            for f in pkg.files:
                if f.startswith(("usr/", "etc/", "lib/", "bin/", "sbin/", "var/", "opt/")):
                    full = "/" + f
                    if os.path.isfile(full) or os.path.islink(full):
                        os.remove(full)
                    elif os.path.isdir(full) and not os.listdir(full):
                        os.rmdir(full)

            # 运行 postrm
            postrm = f"{scripts_dir}/{package_name}.postrm"
            if os.path.exists(postrm):
                scripts_env.run_script(postrm, package_name, pkg.version, pkg.arch, "postrm")

            tx.remove_package(pkg)

            if purge:
                # 删除配置文件
                for f in pkg.files:
                    if f.startswith("etc/"):
                        full = "/" + f
                        if os.path.exists(full):
                            os.remove(full)

        print(f"  ✅ {package_name} 已卸载")
        return True

    def autoremove(self) -> List[str]:
        """自动移除不再需要的依赖"""
        # 找出没有被任何已安装包依赖的包
        needed = set()
        for pkg in self.db.installed_packages():
            for dep_str in pkg.depends:
                for alt in dep_str.split("|"):
                    name = alt.strip().split()[0].split(":")[0].strip()
                    needed.add(name)

        to_remove = []
        for pkg in self.db.installed_packages():
            if pkg.name not in needed and not pkg.locked:
                # 检查是不是手动安装的（简单判断：不在任何依赖里）
                to_remove.append(pkg.name)

        return to_remove

# === 单例 ===

_engine = None

def get_engine() -> InstallEngine:
    global _engine
    if _engine is None:
        _engine = InstallEngine()
    return _engine

# === CLI 入口 ===

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法:")
        print("  python -m xpm_suite.core.installer update")
        print("  python -m xpm_suite.core.installer search <keyword>")
        print("  python -m xpm_suite.core.installer install <pkg>")
        sys.exit(1)

    eng = get_engine()
    cmd = sys.argv[1]

    if cmd == "update":
        eng.update_index()
        print(f"✅ 索引更新完成，共 {len(eng.index.packages)} 个包")
    elif cmd == "search":
        kw = sys.argv[2] if len(sys.argv) > 2 else ""
        results = eng.search(kw)
        for r in results:
            print(f"  {r['name']:<30} {r['version']:<15} {r['description'][:50]}")
    elif cmd == "install":
        pkg = sys.argv[2] if len(sys.argv) > 2 else ""
        eng.install(pkg)
    else:
        print(f"未知命令: {cmd}")

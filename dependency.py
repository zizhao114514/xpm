#!/usr/bin/env python3
"""
dependency.py - XPM 依赖解析器
解析 Packages.gz 中的 Depends 字段，构建依赖图，拓扑排序。
石油驱动，apt 禁止。
"""

import re
from collections import defaultdict, deque

class DependencyError(Exception):
    pass

class DependencyResolver:
    """从解析好的包索引中解析依赖关系"""

    def __init__(self, package_index):
        """
        package_index: dict
            name -> { version, depends, pre_depends, ... }
        即 load_all_packages() 的返回值
        """
        self.index = package_index
        self.installed = {}  # name -> version, 由外部填充

    def set_installed(self, installed):
        """设置已安装包列表 {name: version}"""
        self.installed = installed

    def parse_depends_string(self, dep_string):
        """
        解析 Depends 字段字符串，返回列表：
        [
            [("libc6", ">= 2.34"), ("libc6-alt", None)],  # OR 组
            [("vim-common", None)],
        ]
        每个元素是一个 OR 组（列表），组内任一满足即可。
        """
        if not dep_string:
            return []
        # 按逗号分割（不同依赖），按 | 分割（OR）
        groups = []
        for part in dep_string.split(","):
            part = part.strip()
            if not part:
                continue
            or_group = []
            for alt in part.split("|"):
                alt = alt.strip()
                # 提取包名和版本约束
                m = re.match(r"^(\S+?)\s*(\(.*?\))?\s*\[.*?\]?\s*$", alt)
                if m:
                    pkg = m.group(1).strip()
                    ver = m.group(2).strip() if m.group(2) else None
                else:
                    # 简单匹配
                    pkg = alt.split("(")[0].strip()
                    ver = None
                    paren = re.search(r"\((.*?)\)", alt)
                    if paren:
                        ver = paren.group(1).strip()
                # 清理包名中的架构后缀 :any :native
                pkg = re.sub(r":(any|native)$", "", pkg)
                or_group.append((pkg, ver))
            if or_group:
                groups.append(or_group)
        return groups

    def parse_version_constraint(self, constraint):
        """将 '>= 2.34' 解析为 (op, version)"""
        if not constraint:
            return None
        m = re.match(r"^\s*(<=|>=|<|>|=)\s*(.+?)\s*$", constraint)
        if m:
            return (m.group(1), m.group(2))
        return None

    def version_compare(self, v1, op, v2):
        """Debian 风格版本比较（简化版）"""
        n1 = self._version_to_tuple(v1)
        n2 = self._version_to_tuple(v2)
        if op == "=":
            return n1 == n2
        elif op == ">=":
            return n1 >= n2
        elif op == ">":
            return n1 > n2
        elif op == "<=":
            return n1 <= n2
        elif op == "<":
            return n1 < n2
        return False

    def _version_to_tuple(self, v):
        """将版本字符串转为可比较的元组"""
        # 处理 epoch:upstream-debian
        epoch = 0
        if ":" in v:
            epoch_str, v = v.split(":", 1)
            try:
                epoch = int(epoch_str)
            except:
                epoch = 0
        # 分离 debian revision
        upstream = v
        revision = ""
        if "-" in v:
            parts = v.rsplit("-", 1)
            # 检查第二部分是否像 revision（字母开头）
            if re.match(r"^[a-zA-Z]", parts[1]):
                upstream = parts[0]
                revision = parts[1]
        # 将 upstream 按非数字分割
        upstream_parts = re.split(r"(\d+)", upstream)
        result = [epoch]
        for p in upstream_parts:
            if p.isdigit():
                result.append(int(p))
            elif p:
                result.append(p)
        if revision:
            rev_parts = re.split(r"(\d+)", revision)
            for p in rev_parts:
                if p.isdigit():
                    result.append(int(p))
                elif p:
                    result.append(p)
        return tuple(result)

    def is_satisfied(self, pkg_name, constraint, available):
        """
        检查 (pkg_name, constraint) 是否被 available 满足。
        available: {name: version} 或 None（查索引最新版）
        """
        if available is None:
            # 查索引
            if pkg_name not in self.index:
                return False
            avail_ver = self.index[pkg_name].get("version", "")
        else:
            if pkg_name not in available:
                return False
            avail_ver = available[pkg_name]

        if constraint is None:
            return True
        parsed = self.parse_version_constraint(constraint)
        if parsed is None:
            return True
        op, ver = parsed
        return self.version_compare(avail_ver, op, ver)

    def resolve(self, target_packages, operation="install"):
        """
        核心解析函数。
        target_packages: list of package names to install/remove
        operation: "install" | "remove" | "upgrade"

        返回:
        {
            "install": [pkg_name, ...],   # 需要安装/升级的包（拓扑序）
            "remove": [pkg_name, ...],    # 需要卸载的包
            "conflicts": [...],           # 冲突列表
            "missing": [...],             # 找不到的包
        }
        """
        result = {
            "install": [],
            "remove": [],
            "conflicts": [],
            "missing": [],
        }

        if operation == "install":
            install_list, missing = self._resolve_install(target_packages)
            result["install"] = install_list
            result["missing"] = missing
        elif operation == "remove":
            remove_list, orphans = self._resolve_remove(target_packages)
            result["remove"] = remove_list
            result["orphans"] = orphans
        elif operation == "upgrade":
            upgrade_list, missing = self._resolve_upgrade(target_packages)
            result["install"] = upgrade_list
            result["missing"] = missing

        return result

    def _resolve_install(self, targets):
        """解析安装依赖，返回 (有序安装列表, 缺失列表)"""
        to_install = []  # 最终拓扑序
        visiting = set()
        visited = set()
        missing = []

        def visit(pkg_name, path):
            if pkg_name in visited:
                return
            if pkg_name in visiting:
                raise DependencyError(
                    f"循环依赖: {' -> '.join(path + [pkg_name])}"
                )
            if pkg_name in self.installed:
                # 已安装，检查版本是否满足
                visited.add(pkg_name)
                return
            if pkg_name not in self.index:
                missing.append(pkg_name)
                visited.add(pkg_name)
                return

            visiting.add(pkg_name)
            path = path + [pkg_name]

            pkg_info = self.index[pkg_name]
            deps = self.parse_depends_string(pkg_info.get("depends", ""))

            for or_group in deps:
                satisfied = False
                for dep_name, constraint in or_group:
                    # 检查是否已安装且满足
                    if dep_name in self.installed:
                        if self.is_satisfied(dep_name, constraint, self.installed):
                            satisfied = True
                            break
                    # 检查索引中是否有
                    if dep_name in self.index:
                        idx_ver = self.index[dep_name].get("version", "")
                        if constraint is None or self.version_compare(
                            idx_ver,
                            *self.parse_version_constraint(constraint) or ("=", idx_ver)
                        ):
                            visit(dep_name, path)
                            satisfied = True
                            break
                if not satisfied:
                    # OR 组都不满足
                    result["conflicts"].append({
                        "package": pkg_name,
                        "unsatisfied": or_group,
                    })

            visiting.discard(pkg_name)
            visited.add(pkg_name)
            to_install.append(pkg_name)

        result = {"conflicts": []}
        for target in targets:
            visit(target, [])

        return to_install, missing

    def _resolve_remove(self, targets):
        """解析卸载，返回需要卸载的包 + 可能变成孤儿的包"""
        to_remove = set()
        for target in targets:
            if target in self.installed:
                to_remove.add(target)

        # 找反向依赖：谁依赖这些要删的包
        orphans = []
        for installed_name in list(self.installed.keys()):
            if installed_name in to_remove:
                continue
            info = self.index.get(installed_name, {})
            deps = self.parse_depends_string(info.get("depends", ""))
            for or_group in deps:
                for dep_name, _ in or_group:
                    if dep_name in to_remove:
                        orphans.append(installed_name)
                        break

        return list(to_remove), orphans

    def _resolve_upgrade(self, targets):
        """解析升级：安装索引中版本更新的包"""
        to_upgrade = []
        missing = []
        for target in targets:
            if target not in self.installed:
                missing.append(target)
                continue
            if target not in self.index:
                missing.append(target)
                continue
            installed_ver = self.installed[target]
            available_ver = self.index[target].get("version", "")
            if self.version_compare(available_ver, ">", installed_ver):
                to_upgrade.append(target)
        # 对要升级的包做依赖解析
        install_list, miss2 = self._resolve_install(to_upgrade)
        return install_list, missing + miss2


def load_all_packages(cache_dir="/var/cache/xpm"):
    """
    解析 /var/cache/xpm/*-Packages 文件，返回索引。
    每条记录: name -> {version, depends, ...}
    """
    import glob, os
    index = {}
    for f in glob.glob(f"{cache_dir}/*-Packages"):
        if f.endswith(".gz"):
            continue
        with open(f) as fh:
            current = None
            for line in fh:
                line = line.rstrip("\n")
                if line.startswith("Package:"):
                    name = line.split(":", 1)[1].strip()
                    current = {"package": name}
                    index[name] = current
                elif line.startswith("Version:") and current is not None:
                    current["version"] = line.split(":", 1)[1].strip()
                elif line.startswith("Depends:") and current is not None:
                    current["depends"] = line.split(":", 1)[1].strip()
                elif line.startswith("Pre-Depends:") and current is not None:
                    current["pre_depends"] = line.split(":", 1)[1].strip()
                elif line.startswith("Conflicts:") and current is not None:
                    current["conflicts"] = line.split(":", 1)[1].strip()
                elif line.startswith("Provides:") and current is not None:
                    current["provides"] = line.split(":", 1)[1].strip()
                elif line.startswith("Architecture:") and current is not None:
                    current["architecture"] = line.split(":", 1)[1].strip()
                elif line.startswith("Filename:") and current is not None:
                    current["filename"] = line.split(":", 1)[1].strip()
                elif line.startswith("Size:") and current is not None:
                    current["size"] = line.split(":", 1)[1].strip()
                elif line.startswith("SHA256:") and current is not None:
                    current["sha256"] = line.split(":", 1)[1].strip()
    return index


def get_installed_packages(status_db="/var/lib/xpm/status.db"):
    """从 XPM 数据库读取已安装包 {name: version}"""
    installed = {}
    if not os.path.exists(status_db):
        return installed
    current = None
    with open(status_db) as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("Package:"):
                name = line.split(":", 1)[1].strip()
                current = {"package": name}
                installed[name] = current
            elif line.startswith("Version:") and current is not None:
                current["version"] = line.split(":", 1)[1].strip()
            elif line == "" and current is not None:
                current = None
    # 简化：返回 {name: version}
    result = {}
    for name, info in installed.items():
        result[name] = info.get("version", "0")
    return result


if __name__ == "__main__":
    # 简单测试
    idx = load_all_packages()
    installed = get_installed_packages()
    resolver = DependencyResolver(idx)
    resolver.set_installed(installed)
    print(f"索引包数: {len(idx)}")
    print(f"已安装: {len(installed)}")
    # 测试版本比较
    print(f"1.2.3 > 1.2.2: {resolver.version_compare('1.2.3', '>', '1.2.2')}")
    print(f"2:1.0 > 1:1.0: {resolver.version_compare('2:1.0', '>', '1:1.0')}")

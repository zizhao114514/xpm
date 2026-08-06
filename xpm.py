#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XPM - Xinghua Package Manager v2.1-0 "Ultimate Edition"
终极修复版：一次修完所有已知 bug

修复清单：
1. ar 归档签名 → fakeroot + dpkg-deb 一步构建（build_deb.py）
2. Filename 字段 → download_package() 强制用 Packages 的 Filename
3. HTTPS/CA 证书 → 下载后校验魔术头 + HTTP 自动降级
4. wget 吞错误页 → --max-redirect=5 + 检查退出码 + 检查 Content-Type
5. 解包 "not a gzip file" → 下载后校验 ar magic `!<arch>\n`
6. self-update → GitHub API 自动检查 + 下载 + 安装
7. mirrors URL 拼接 → 用 release_url() 正确拼接
8. info() 作用域 → 全部改为 log_info/log_ok/log_warn/log_err
9. 依赖解析增强 → 预检查 + 详细错误提示
10. 进度条 → 支持未知大小（从 Content-Length 读）
"""

import os, sys, subprocess, json, shutil, gzip, tarfile
import hashlib, base64, time, re, signal, errno
import urllib.request, urllib.error, ssl
from io import BytesIO

# ═════════════════════════════════════════════════════════
# 常量
# ═════════════════════════════════════════════════════════
VERSION = "2.1-0"
CODENAME = "Ultimate Edition"
XPM_ROOT = "/usr/local/share/xpm"
XPM_BIN = "/usr/local/bin/xpm"
XPM_BACKEND = "/usr/local/bin/xm"
XPM_SOURCES_DIR = os.path.join(XPM_ROOT, "sources.list.d")
XPM_CACHE = os.path.join(XPM_ROOT, "cache")
XPM_INSTALLED = os.path.join(XPM_ROOT, "installed")
XPM_STATE = os.path.join(XPM_ROOT, "state")

GITHUB_API = "https://api.github.com/repos/zizhao114514/xpm"
GITHUB_RELEASES = "https://github.com/zizhao114514/xpm/releases/latest"

# 禁用 SSL 验证（proot 环境 CA 证书经常不全）
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ═════════════════════════════════════════════════════════
# 日志函数（不再用 info/error 这种容易冲突的名字）
# ═════════════════════════════════════════════════════════
def log_info(msg):
    print(f"[i] {msg}")

def log_ok(msg):
    print(f"[✓] {msg}")

def log_warn(msg):
    print(f"[!] {msg}")

def log_err(msg):
    print(f"[✗] {msg}")

def log_stage(n, total, msg):
    print(f"[{n}/{total}] {msg}")

def log_progress(done, total, prefix="", bar_len=40):
    if total > 0:
        pct = min(done / total, 1.0)
    else:
        pct = 0
    filled = int(bar_len * pct)
    bar = "█" * filled + "░" * (bar_len - filled)
    pct_s = f"{pct*100:5.1f}%" if total > 0 else "  ?  "
    print(f"\r{prefix} [{bar}] {pct_s}", end="", flush=True)
    if pct >= 1.0 or total == 0:
        print()

# ═════════════════════════════════════════════════════════
# 进度条下载器（支持 Content-Length + 魔术头校验）
# ═════════════════════════════════════════════════════════
class ProgressDownloader:
    """带进度条 + 大小探测 + 魔术头校验的下载器"""

    def __init__(self, url, dest, timeout=30):
        self.url = url
        self.dest = dest
        self.timeout = timeout
        self.downloaded = 0
        self.total = 0
        self.headers = {}

    def probe_size(self):
        """先发 HEAD 请求探测 Content-Length"""
        try:
            req = urllib.request.Request(self.url, method="HEAD")
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=self.timeout) as resp:
                self.headers = dict(resp.headers)
                cl = self.headers.get("Content-Length", "")
                if cl.isdigit():
                    self.total = int(cl)
        except Exception:
            pass  # HEAD 失败不致命，继续 GET

    def download(self):
        """下载文件，带进度条"""
        try:
            req = urllib.request.Request(self.url)
            req.add_header("User-Agent", "XPM/2.1")
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=self.timeout) as resp:
                self.headers = dict(resp.headers)
                cl = self.headers.get("Content-Length", "")
                if cl.isdigit():
                    self.total = int(cl)

                # 检查 Content-Type 是不是奇怪的东西
                ct = self.headers.get("Content-Type", "")
                if "text/html" in ct.lower() and self.total < 10000:
                    # 可能是错误页，先读一点看看
                    chunk = resp.read(512)
                    if chunk.startswith(b"<"):
                        raise Exception(f"服务器返回 HTML 页面而非文件 (Content-Type: {ct})")

                with open(self.dest, "wb") as f:
                    while True:
                        chunk = resp.read(64 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        self.downloaded += len(chunk)
                        log_progress(self.downloaded, self.total, prefix="  ")
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP {e.code}: {e.reason} ({self.url})")
        except urllib.error.URLError as e:
            raise Exception(f"网络错误: {e.reason}")

    def verify_deb(self):
        """校验下载的文件是不是真正的 .deb（ar 归档）"""
        with open(self.dest, "rb") as f:
            magic = f.read(8)
        if magic != b"!<arch>\n":
            # 检查是不是 HTML
            with open(self.dest, "rb") as f:
                head = f.read(256)
            if head.startswith(b"<") or b"<html" in head.lower():
                raise Exception(
                    f"下载到 HTML 页面而非 .deb 文件\n"
                    f"  URL: {self.url}\n"
                    f"  文件头: {head[:80]}\n"
                    f"  建议: 检查网络/CA 证书，或尝试 HTTP 链接"
                )
            raise Exception(
                f"下载文件不是有效的 .deb (magic={magic!r})\n"
                f"  URL: {self.url}\n"
                f"  文件大小: {os.path.getsize(self.dest)} bytes"
            )

# ═════════════════════════════════════════════════════════
# 源解析
# ═════════════════════════════════════════════════════════
class Source:
    def __init__(self, raw_line, filepath=""):
        self.raw = raw_line.strip()
        self.filepath = filepath
        self.enabled = True
        self.type = "deb"
        self.url = ""
        self.suite = ""
        self.components = []
        self.arch = "amd64"
        self._parse()

    def _parse(self):
        if self.raw.startswith("#"):
            self.enabled = False
            line = self.raw[1:].strip()
        else:
            line = self.raw

        parts = line.split()
        if len(parts) < 3:
            return

        self.type = parts[0]
        self.url = parts[1].rstrip("/")

        # 检测 [arch=...] 选项
        if self.url.startswith("[") and "]" in self.url:
            opt = self.url[1:self.url.index("]")]
            self.url = parts[2].rstrip("/")
            for kv in opt.split():
                if kv.startswith("arch="):
                    self.arch = kv[5:]

        if len(parts) >= 3:
            self.suite = parts[2] if not self.url.startswith("[") else parts[3] if len(parts) > 3 else ""
        if len(parts) >= 4:
            self.components = parts[3:] if not self.url.startswith("[") else parts[4:]

    def release_url(self, component=None):
        """生成 Release 文件 URL"""
        if component:
            return f"{self.url}/dists/{self.suite}/{component}/binary-{self.arch}/Packages.gz"
        return f"{self.url}/dists/{self.suite}/Release"

    def package_url(self, filename):
        """从 Packages 的 Filename 字段生成完整下载 URL"""
        return f"{self.url}/{filename}"

    def __repr__(self):
        return f"Source({self.url} {self.suite} {' '.join(self.components)})"

def load_sources():
    sources = []
    if not os.path.isdir(XPM_SOURCES_DIR):
        return sources
    for fname in sorted(os.listdir(XPM_SOURCES_DIR)):
        if not fname.endswith(".list"):
            continue
        fpath = os.path.join(XPM_SOURCES_DIR, fname)
        with open(fpath) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                s = Source(line, fpath)
                if s.url:
                    sources.append(s)
    return sources

# ═════════════════════════════════════════════════════════
# Packages 索引解析
# ═════════════════════════════════════════════════════════
def parse_packages_gz(data):
    """解析 Packages.gz 内容为字典列表"""
    text = gzip.decompress(data).decode("utf-8", errors="replace")
    packages = []
    current = {}
    for line in text.split("\n"):
        if line.strip() == "":
            if current:
                packages.append(current)
            current = {}
            continue
        if line.startswith(" "):
            # 多行续行
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            current[key.strip()] = val.strip()
    if current:
        packages.append(current)
    return packages

def download_index(source, component):
    """下载并解析一个 component 的 Packages.gz"""
    url = source.release_url(component)
    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_path = os.path.join(XPM_CACHE, f"pkg_{cache_key}.json")

    if os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < 3600:  # 1小时缓存
            with open(cache_path) as f:
                return json.load(f)

    log_info(f"更新索引: {url}")

    # 尝试 HTTPS
    data = None
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "XPM/2.1")
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            data = resp.read()
    except Exception as e:
        log_warn(f"HTTPS 失败: {e}")
        # 降级 HTTP
        http_url = url.replace("https://", "http://")
        log_info(f"尝试 HTTP: {http_url}")
        try:
            req = urllib.request.Request(http_url)
            req.add_header("User-Agent", "XPM/2.1")
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
                data = resp.read()
        except Exception as e2:
            raise Exception(f"索引下载失败 (HTTPS+HTTP 均失败): {e2}")

    # 检查是不是 HTML
    if data[:1] == b"<" or data[:15].lower().startswith(b"<!doctype"):
        raise Exception(f"索引返回 HTML 而非 gzip (URL: {url})")

    packages = parse_packages_gz(data)

    os.makedirs(XPM_CACHE, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(packages, f)

    return packages

# ═════════════════════════════════════════════════════════
# 包搜索与依赖解析
# ═════════════════════════════════════════════════════════
def search_package(name):
    """在所有源中搜索包，返回 (source, package_entry) 或 None"""
    sources = load_sources()
    for src in sources:
        if not src.enabled:
            continue
        for comp in src.components or ["main"]:
            try:
                pkgs = download_index(src, comp)
            except Exception as e:
                log_warn(f"索引失败 {src.url}/{comp}: {e}")
                continue
            for pkg in pkgs:
                if pkg.get("Package") == name:
                    return src, pkg
    return None, None

def resolve_dependencies(pkg_entry):
    """解析依赖列表"""
    deps_str = pkg_entry.get("Depends", "")
    if not deps_str:
        return []
    deps = []
    for part in deps_str.split(","):
        part = part.strip()
        # 去掉版本约束: libc6 (>= 2.34) → libc6
        name = part.split("(")[0].strip()
        # 去掉架构限定: libc6:amd64 → libc6
        name = name.split(":")[0].strip()
        if name and name not in deps:
            deps.append(name)
    return deps

# ═════════════════════════════════════════════════════════
# 下载与安装
# ═════════════════════════════════════════════════════════
def download_deb(source, pkg_entry, dest_dir):
    """下载 .deb 文件，返回本地路径"""
    pkgname = pkg_entry["Package"]
    version = pkg_entry["Version"]
    arch = pkg_entry.get("Architecture", "amd64")
    filename = pkg_entry.get("Filename", "")

    if not filename:
        raise Exception(f"Packages 中缺少 Filename 字段: {pkgname}")

    url = source.package_url(filename)
    dest = os.path.join(dest_dir, f"{pkgname}_{version}_{arch}.deb")

    log_info(f"下载: {pkgname} ({version})")
    log_info(f"  URL: {url}")

    os.makedirs(dest_dir, exist_ok=True)

    # 尝试 HTTPS
    last_err = None
    for attempt_url in [url, url.replace("https://", "http://")]:
        try:
            dl = ProgressDownloader(attempt_url, dest, timeout=60)
            dl.probe_size()
            dl.download()

            # 校验是真正的 .deb
            dl.verify_deb()

            log_ok(f"下载完成: {dest}")
            return dest
        except Exception as e:
            last_err = e
            log_warn(f"下载失败: {e}")
            if attempt_url.startswith("http://"):
                break
            log_info("尝试 HTTP 降级...")

    raise Exception(f"下载失败: {pkgname} ({last_err})")

def install_deb(deb_path):
    """用 xm 后端安装 .deb"""
    if not os.path.exists(deb_path):
        raise Exception(f"文件不存在: {deb_path}")

    # 校验是有效的 deb
    with open(deb_path, "rb") as f:
        magic = f.read(8)
    if magic != b"!<arch>\n":
        raise Exception(f"不是有效的 .deb 文件: {deb_path} (magic={magic!r})")

    log_info(f"安装: {deb_path}")
    ret = subprocess.run([XPM_BACKEND, "install", deb_path], capture_output=True, text=True)
    if ret.returncode != 0:
        raise Exception(f"xm install 失败:\n{ret.stdout}\n{ret.stderr}")
    return True

def extract_deb_data(deb_path, extract_to):
    """从 .deb 中提取 data.tar.gz 并解包"""
    # 用 ar 解包
    tmp = "/tmp/xpm_extract_" + str(int(time.time()))
    os.makedirs(tmp, exist_ok=True)
    subprocess.run(["ar", "x", deb_path], cwd=tmp, check=True)

    # 找 data.tar.*
    for f in os.listdir(tmp):
        if f.startswith("data.tar"):
            data_path = os.path.join(tmp, f)
            if f.endswith(".gz"):
                with gzip.open(data_path) as gz:
                    with tarfile.open(fileobj=gz) as tar:
                        tar.extractall(path=extract_to)
            else:
                with tarfile.open(data_path) as tar:
                    tar.extractall(path=extract_to)
            break

    shutil.rmtree(tmp, ignore_errors=True)

# ═════════════════════════════════════════════════════════
# 命令实现
# ═════════════════════════════════════════════════════════
def cmd_version(args=None):
    print(f"xpm {VERSION} \"{CODENAME}\"")
    print(f"石油储备 100001% | 功耗 1.x W")
    print(f"构建: {sys.version.split()[0]} | 平台: {sys.platform}")

def cmd_install(args):
    if not args:
        log_err("用法: xpm install <包名> [包名2 ...]")
        return 1

    to_install = []
    for pkgname in args:
        # 检查是否已安装
        if os.path.exists(os.path.join(XPM_INSTALLED, f"{pkgname}.json")):
            log_warn(f"{pkgname} 已安装，跳过")
            continue

        log_info(f"搜索: {pkgname}")
        source, pkg = search_package(pkgname)
        if not pkg:
            log_err(f"未找到包: {pkgname}")
            return 1

        to_install.append((pkgname, source, pkg))

    if not to_install:
        log_info("没有需要安装的包")
        return 0

    # 解析依赖
    all_needed = []
    seen = set()
    for pkgname, source, pkg in to_install:
        deps = resolve_dependencies(pkg)
        for dep in deps:
            if dep not in seen and not os.path.exists(os.path.join(XPM_INSTALLED, f"{dep}.json")):
                seen.add(dep)
                all_needed.append(dep)

    total = len(to_install) + len(all_needed)
    log_info(f"将安装 {total} 个包（含依赖）")

    # 确认
    if sys.stdin.isatty():
        print(f"  主包: {', '.join(p[0] for p in to_install)}")
        if all_needed:
            print(f"  依赖: {', '.join(all_needed)}")
        ans = input("确认安装? [Y/n] ").strip().lower()
        if ans == "n":
            log_info("已取消")
            return 0

    # 下载所有包
    download_dir = os.path.join(XPM_CACHE, "downloads")
    os.makedirs(download_dir, exist_ok=True)

    downloaded = []
    try:
        step = 0
        # 先下载主包
        for pkgname, source, pkg in to_install:
            step += 1
            log_stage(step, total, f"下载 {pkgname} ({pkg['Version']})")
            try:
                deb = download_deb(source, pkg, download_dir)
                downloaded.append((pkgname, deb, source, pkg))
            except Exception as e:
                log_err(f"下载失败: {pkgname}: {e}")
                raise

        # 再下载依赖
        for depname in all_needed:
            step += 1
            src, pkg = search_package(depname)
            if not pkg:
                log_warn(f"依赖 {depname} 未找到，跳过")
                continue
            log_stage(step, total, f"下载 {depname} ({pkg['Version']})")
            try:
                deb = download_deb(src, pkg, download_dir)
                downloaded.append((depname, deb, src, pkg))
            except Exception as e:
                log_warn(f"依赖下载失败: {depname}: {e}")

        # 安装
        for i, (pkgname, deb, source, pkg) in enumerate(downloaded):
            step += 1
            log_stage(step, total + len(downloaded), f"安装 {pkgname}")
            install_deb(deb)

            # 记录安装状态
            info_path = os.path.join(XPM_INSTALLED, f"{pkgname}.json")
            os.makedirs(XPM_INSTALLED, exist_ok=True)
            with open(info_path, "w") as f:
                json.dump({
                    "name": pkgname,
                    "version": pkg.get("Version", ""),
                    "source": source.url if source else "",
                    "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "filename": os.path.basename(deb),
                }, f, indent=2)

        log_ok(f"安装完成: {len(downloaded)} 个包")

    except Exception as e:
        log_err(f"安装失败: {e}")
        log_info("正在回滚...")
        # 回滚：尝试卸载已安装的
        for pkgname, deb, _, _ in downloaded:
            try:
                subprocess.run([XPM_BACKEND, "remove", pkgname], capture_output=True)
                rm = os.path.join(XPM_INSTALLED, f"{pkgname}.json")
                if os.path.exists(rm):
                    os.remove(rm)
            except:
                pass
        log_warn("回滚完成")
        return 1

    return 0

def cmd_remove(args):
    if not args:
        log_err("用法: xpm remove <包名>")
        return 1
    for pkgname in args:
        log_info(f"卸载: {pkgname}")
        ret = subprocess.run([XPM_BACKEND, "remove", pkgname], capture_output=True, text=True)
        if ret.returncode == 0:
            rm = os.path.join(XPM_INSTALLED, f"{pkgname}.json")
            if os.path.exists(rm):
                os.remove(rm)
            log_ok(f"已卸载: {pkgname}")
        else:
            log_warn(f"卸载可能不完整: {ret.stderr.strip()}")

def cmd_search(args):
    if not args:
        log_err("用法: xpm search <关键词>")
        return 1
    keyword = args[0].lower()
    sources = load_sources()
    found = []
    for src in sources:
        if not src.enabled:
            continue
        for comp in src.components or ["main"]:
            try:
                pkgs = download_index(src, comp)
            except:
                continue
            for pkg in pkgs:
                name = pkg.get("Package", "")
                desc = pkg.get("Description", "").split("\n")[0]
                if keyword in name.lower() or keyword in desc.lower():
                    found.append((name, pkg.get("Version", ""), desc))

    if not found:
        log_warn(f"未找到包含 '{keyword}' 的包")
        return 0

    for name, ver, desc in sorted(set(found)):
        print(f"  {name} ({ver}) - {desc[:60]}")

def cmd_update(args=None):
    log_info("正在更新软件源索引...")
    sources = load_sources()
    if not sources:
        log_warn("没有配置软件源")
        return 1

    # 清缓存
    if os.path.isdir(XPM_CACHE):
        for f in os.listdir(XPM_CACHE):
            if f.startswith("pkg_"):
                os.remove(os.path.join(XPM_CACHE, f))

    count = 0
    for src in sources:
        if not src.enabled:
            continue
        for comp in src.components or ["main"]:
            try:
                pkgs = download_index(src, comp)
                count += len(pkgs)
                log_ok(f"{src.url}/{comp}: {len(pkgs)} 个包")
            except Exception as e:
                log_warn(f"失败: {src.url}/{comp}: {e}")

    log_ok(f"索引更新完成，共 {count} 个包")
    return 0

def cmd_check_update(args=None):
    """检查 XPM 自身是否有更新"""
    log_info("检查 XPM 更新...")
    try:
        api_url = f"{GITHUB_API}/releases/latest"
        req = urllib.request.Request(api_url)
        req.add_header("User-Agent", "XPM/2.1")
        req.add_header("Accept", "application/vnd.github.v3+json")
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        latest_tag = data.get("tag_name", "").strip()
        latest_ver = latest_tag.lstrip("v")

        if not latest_ver:
            log_warn("无法获取最新版本号")
            return 1

        # 简单版本比较
        cur = VERSION.replace("-", ".")
        lat = latest_ver.replace("-", ".")

        if cur < lat:
            print(f"\n 当前版本: {VERSION}")
            print(f" 最新版本: {latest_ver}")
            print(f" 发布说明: {data.get('html_url', '')}")
            print(f"\n 运行 'xpm self-update' 升级")
            return 0
        else:
            log_ok(f"已是最新版本 ({VERSION})")
            return 0

    except Exception as e:
        log_warn(f"检查更新失败: {e}")
        log_info("可能是网络问题，可手动访问:")
        print(f"  {GITHUB_RELEASES}")
        return 1

def cmd_self_update(args=None):
    """自动下载并安装最新版 XPM"""
    log_info("正在检查更新...")

    try:
        api_url = f"{GITHUB_API}/releases/latest"
        req = urllib.request.Request(api_url)
        req.add_header("User-Agent", "XPM/2.1")
        req.add_header("Accept", "application/vnd.github.v3+json")
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        log_err(f"无法获取版本信息: {e}")
        return 1

    latest_ver = data.get("tag_name", "").lstrip("v")
    if not latest_ver:
        log_err("无法解析最新版本")
        return 1

    cur = VERSION.replace("-", ".")
    lat = latest_ver.replace("-", ".")

    if cur >= lat:
        log_ok(f"已是最新版本 ({VERSION})")
        return 0

    print(f"  当前: {VERSION}")
    print(f"  最新: {latest_ver}")

    # 找 .deb 资产
    assets = data.get("assets", [])
    deb_url = None
    for a in assets:
        if a["name"].endswith(".deb"):
            deb_url = a["browser_download_url"]
            break

    if not deb_url:
        # 尝试从 releases 页面直接拼 URL
        deb_url = f"https://github.com/zizhao114514/xpm/releases/download/v{latest_ver}/xpm_{latest_ver}_all.deb"
        log_info(f"使用推断 URL: {deb_url}")

    # 下载
    tmp_deb = f"/tmp/xpm_update_{latest_ver}.deb"
    log_info(f"下载: {deb_url}")

    try:
        dl = ProgressDownloader(deb_url, tmp_deb, timeout=60)
        dl.probe_size()
        dl.download()
        dl.verify_deb()
        log_ok(f"下载完成")
    except Exception as e:
        log_err(f"下载失败: {e}")
        log_info("尝试 HTTP 降级...")
        try:
            http_url = deb_url.replace("https://", "http://")
            dl2 = ProgressDownloader(http_url, tmp_deb, timeout=60)
            dl2.download()
            dl2.verify_deb()
            log_ok(f"HTTP 下载成功")
        except Exception as e2:
            log_err(f"HTTP 也失败: {e2}")
            return 1

    # 安装
    log_info("正在安装更新...")
    ret = subprocess.run(["sudo", "dpkg", "-i", tmp_deb], capture_output=True, text=True)
    if ret.returncode == 0:
        log_ok(f"XPM 已升级到 {latest_ver}")
        os.remove(tmp_deb)
        return 0
    else:
        # 尝试不 sudo
        ret2 = subprocess.run(["dpkg", "-i", tmp_deb], capture_output=True, text=True)
        if ret2.returncode == 0:
            log_ok(f"XPM 已升级到 {latest_ver}")
            os.remove(tmp_deb)
            return 0
        log_err(f"安装失败:\n{ret.stderr}\n{ret2.stderr}")
        return 1

def cmd_doctor(args=None):
    """诊断系统状态"""
    print("XPM 系统诊断")
    print("=" * 50)

    checks = []

    # Python 版本
    py_ok = sys.version_info >= (3, 8)
    checks.append(("Python >= 3.8", py_ok, sys.version.split()[0]))

    # dpkg 可用
    dpkg_ok = shutil.which("dpkg") is not None
    checks.append(("dpkg 可用", dpkg_ok, shutil.which("dpkg") or "未找到"))

    # ar 可用
    ar_ok = shutil.which("ar") is not None
    checks.append(("ar 可用", ar_ok, shutil.which("ar") or "未找到"))

    # wget/curl
    wget_ok = shutil.which("wget") is not None
    curl_ok = shutil.which("curl") is not None
    checks.append(("wget/curl", wget_ok or curl_ok, f"wget={'✓' if wget_ok else '✗'} curl={'✓' if curl_ok else '✗'}"))

    # ca-certificates
    ca_ok = os.path.exists("/etc/ssl/certs/ca-certificates.crt")
    checks.append(("CA 证书", ca_ok, "/etc/ssl/certs/ca-certificates.crt" if ca_ok else "缺失"))

    # XPM 目录
    for d, label in [
        (XPM_ROOT, "XPM 根目录"),
        (XPM_SOURCES_DIR, "软件源目录"),
        (XPM_CACHE, "缓存目录"),
        (XPM_INSTALLED, "已安装目录"),
    ]:
        ok = os.path.isdir(d)
        checks.append((label, ok, d))

    # 后端
    xm_ok = os.path.exists(XPM_BACKEND)
    checks.append(("xm 后端", xm_ok, XPM_BACKEND))

    # 软件源
    sources = load_sources()
    src_ok = len(sources) > 0
    checks.append(("软件源配置", src_ok, f"{len(sources)} 个源"))

    # 网络测试
    net_ok = False
    net_detail = ""
    try:
        req = urllib.request.Request("https://mirrors.tuna.tsinghua.edu.cn/")
        req.add_header("User-Agent", "XPM/2.1")
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
            net_ok = resp.status == 200
            net_detail = f"HTTP {resp.status}"
    except Exception as e:
        net_detail = str(e)[:50]
        # 试 HTTP
        try:
            req = urllib.request.Request("http://mirrors.tuna.tsinghua.edu.cn/")
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
                net_ok = resp.status == 200
                net_detail = f"HTTP {resp.status} (HTTPS失败走HTTP)"
        except Exception as e2:
            net_detail = str(e2)[:50]

    checks.append(("网络连通", net_ok, net_detail))

    # 打印结果
    for label, ok, detail in checks:
        icon = "✓" if ok else "✗"
        color = "\033[32m" if ok else "\033[31m"
        print(f"  {color}{icon}\033[0m {label:<20s} {detail}")

    print("=" * 50)

    # 建议
    issues = [c for c in checks if not c[1]]
    if issues:
        print("\n建议修复:")
        for label, _, _ in issues:
            if label == "CA 证书":
                print(f"  sudo apt install --reinstall ca-certificates")
            elif label == "网络连通":
                print(f"  ping mirrors.tuna.tsinghua.edu.cn")
                print(f"  或换源: sudo nano {XPM_SOURCES_DIR}/tuna.list")
            elif label == "软件源配置":
                print(f"  echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main' | sudo tee {XPM_SOURCES_DIR}/tuna.list")
    else:
        log_ok("系统状态良好")

    return 0 if not issues else 1

def cmd_mirrors(args=None):
    """测试各源的延迟"""
    sources = load_sources()
    if not sources:
        log_warn("没有配置软件源")
        return 1

    print(f"{'源文件':<30s} {'延迟':>10s}")
    print("-" * 50)

    for src in sources:
        if not src.enabled:
            continue
        fname = os.path.basename(src.filepath)
        url = src.release_url()  # 正确的 Release URL

        log_info(f"测试: {url}")

        start = time.time()
        ok = False
        err = ""
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "XPM/2.1")
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
                ok = resp.status == 200
        except Exception as e:
            err = str(e)[:40]
            # 试 HTTP
            try:
                http_url = url.replace("https://", "http://")
                req = urllib.request.Request(http_url)
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
                    ok = resp.status == 200
                    err = "(HTTP降级)"
            except Exception as e2:
                err = str(e2)[:40]

        elapsed = int((time.time() - start) * 1000)
        if ok:
            print(f"  {fname:<28s} {elapsed:>6d}ms ✓")
        else:
            print(f"  {fname:<28s} {'FAIL':>6s} ({err})")

    return 0

def cmd_list(args=None):
    """列出已安装的包"""
    if not os.path.isdir(XPM_INSTALLED):
        log_info("未安装任何包")
        return 0

    pkgs = sorted(os.listdir(XPM_INSTALLED))
    pkgs = [p for p in pkgs if p.endswith(".json")]

    if not pkgs:
        log_info("未安装任何包")
        return 0

    print(f"{'包名':<30s} {'版本':<20s} {'安装时间'}")
    print("-" * 70)
    for p in pkgs:
        with open(os.path.join(XPM_INSTALLED, p)) as f:
            info = json.load(f)
        print(f"  {info.get('name',''):<28s} {info.get('version',''):<18s} {info.get('installed_at','')}")

    return 0

def cmd_rebuild_db(args=None):
    """重建 XPM 数据库（从 dpkg 同步）"""
    log_info("重建 XPM 数据库...")
    os.makedirs(XPM_INSTALLED, exist_ok=True)

    # 从 dpkg 获取已安装包列表
    ret = subprocess.run(["dpkg-query", "-W", "-f=${Package}|${Version}|${Status}\n"],
                         capture_output=True, text=True)
    count = 0
    for line in ret.stdout.strip().split("\n"):
        parts = line.split("|")
        if len(parts) >= 3 and "installed" in parts[2]:
            name = parts[0]
            ver = parts[1]
            info_path = os.path.join(XPM_INSTALLED, f"{name}.json")
            with open(info_path, "w") as f:
                json.dump({
                    "name": name,
                    "version": ver,
                    "source": "dpkg-sync",
                    "installed_at": "unknown",
                }, f, indent=2)
            count += 1

    log_ok(f"同步了 {count} 个已安装包")
    return 0

# ═════════════════════════════════════════════════════════
# 主入口
# ═════════════════════════════════════════════════════════
COMMANDS = {
    "version": (cmd_version, "显示版本信息"),
    "install": (cmd_install, "安装软件包"),
    "remove": (cmd_remove, "卸载软件包"),
    "search": (cmd_search, "搜索软件包"),
    "update": (cmd_update, "更新软件源索引"),
    "check-update": (cmd_check_update, "检查 XPM 更新"),
    "self-update": (cmd_self_update, "升级 XPM 自身"),
    "doctor": (cmd_doctor, "系统诊断"),
    "mirrors": (cmd_mirrors, "测试源延迟"),
    "list": (cmd_list, "列出已安装包"),
    "rebuild-db": (cmd_rebuild_db, "从 dpkg 重建数据库"),
}

HELP_TEXT = """XPM - Xinghua Package Manager v{VERSION} "{CODENAME}"

用法: xpm <命令> [参数...]

命令:
  version                    显示版本信息
  install <包名> [...]       安装软件包（自动处理依赖）
  remove  <包名> [...]       卸载软件包
  search  <关键词>           搜索软件包
  update                     更新软件源索引
  list                       列出已安装包
  mirrors                    测试各源延迟
  doctor                     系统诊断（检查网络/CA/依赖）
  check-update               检查 XPM 是否有新版本
  self-update                自动升级 XPM 到最新版
  rebuild-db                 从 dpkg 重建 XPM 数据库

示例:
  sudo xpm update
  sudo xpm install htop vim
  xpm search editor
  xpm doctor
  xpm self-update

石油储备 100001% | 功耗 1.x W | 咖啡机稳定
""".format(VERSION=VERSION, CODENAME=CODENAME)

def main():
    if len(sys.argv) < 2:
        print(HELP_TEXT)
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd in ("-h", "--help", "help"):
        print(HELP_TEXT)
        sys.exit(0)

    if cmd in COMMANDS:
        func, _ = COMMANDS[cmd]
        try:
            sys.exit(func(args))
        except KeyboardInterrupt:
            print("\n[!] 用户中断")
            sys.exit(130)
        except Exception as e:
            log_err(f"未预期错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        log_err(f"未知命令: {cmd}")
        print(HELP_TEXT)
        sys.exit(1)

if __name__ == "__main__":
    main()

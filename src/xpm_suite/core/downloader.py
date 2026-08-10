"""
XPM Suite 多线程下载器
支持: 分块并行 / 断点续传 / 镜像切换 / 指数退避 / 带宽限制 / SHA256校验
"""

import os, hashlib, json, time, threading, socket
from typing import List, Optional, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# === 镜像管理 ===

class Mirror:
    def __init__(self, name: str, base_url: str, weight: int = 100):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.weight = weight
        self.latency = None  # 毫秒
        self.failures = 0
        self.last_success = 0

    def full_url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def __repr__(self):
        lat = f"{self.latency:.0f}ms" if self.latency else "?"
        return f"Mirror({self.name}, {lat}, w={self.weight})"

class MirrorManager:
    """管理多个镜像，按延迟排序 + 故障转移"""

    def __init__(self):
        self.mirrors: List[Mirror] = []
        self._load_defaults()

    def _load_defaults(self):
        defaults = [
            ("Tuna",       "https://mirrors.tuna.tsinghua.edu.cn", 100),
            ("USTC",       "https://mirrors.ustc.edu.cn",          90),
            ("Aliyun",     "https://mirrors.aliyun.com",            85),
            ("Debian官方", "https://deb.debian.org",                50),
            ("163",        "https://mirrors.163.com",               80),
        ]
        for n, u, w in defaults:
            self.mirrors.append(Mirror(n, u, w))

    def add(self, name: str, url: str, weight: int = 100):
        self.mirrors.append(Mirror(name, url, weight))

    def measure_latency(self, timeout=5) -> List[Mirror]:
        """测所有镜像延迟"""
        for m in self.mirrors:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                start = time.time()
                host = m.base_url.split("//")[1].split("/")[0]
                s.connect((host, 443 if m.base_url.startswith("https") else 80))
                m.latency = (time.time() - start) * 1000
                s.close()
            except Exception:
                m.latency = None
                m.failures += 1
        # 排序：有延迟的优先，按延迟升序
        self.mirrors.sort(key=lambda m: (m.latency is None, m.latency or 9999))
        return self.mirrors

    def best(self) -> Optional[Mirror]:
        alive = [m for m in self.mirrors if m.latency is not None and m.failures < 3]
        return alive[0] if alive else (self.mirrors[0] if self.mirrors else None)

    def next_after_failure(self, failed: Mirror) -> Optional[Mirror]:
        failed.failures += 1
        idx = self.mirrors.index(failed) if failed in self.mirrors else -1
        for m in self.mirrors[idx+1:]:
            if m.failures < 3:
                return m
        return None

# === 分块下载 ===

class ChunkDownloader:
    """多线程分块下载 + 断点续传"""

    def __init__(self, mirror_mgr: MirrorManager, threads: int = 4,
                 chunk_size: int = 1024*1024, timeout: int = 30,
                 retry: int = 5, backoff_base: int = 2,
                 bandwidth_limit: int = 0):
        self.mgr = mirror_mgr
        self.threads = max(1, min(threads, 16))
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.retry = retry
        self.backoff_base = backoff_base
        self.bandwidth_limit = bandwidth_limit  # bytes/sec, 0=不限
        self._progress_cb = None
        self._stop = False

    def set_progress_callback(self, cb: Callable[[int, int, str], None]):
        """cb(downloaded, total, current_chunk_info)"""
        self._progress_cb = cb

    def _http_get_range(self, url: str, start: int, end: int,
                        mirror: Mirror) -> bytes:
        """下载指定字节范围，带重试和指数退避"""
        last_err = None
        try:
            from .version import get_short_version
            ua = f"XPM-Suite/{get_short_version()}"
        except ImportError:
            ua = "XPM-Suite/3.1"
        for attempt in range(self.retry):
            try:
                req = Request(url)
                req.add_header("Range", f"bytes={start}-{end}")
                req.add_header("User-Agent", ua)
                with urlopen(req, timeout=self.timeout) as resp:
                    return resp.read()
            except HTTPError as e:
                if e.code == 416:  # Range Not Satisfiable
                    return b""
                last_err = f"HTTP {e.code}"
            except (URLError, socket.timeout) as e:
                last_err = str(e)
            except Exception as e:
                last_err = str(e)

            # 指数退避
            delay = self.backoff_base ** attempt
            time.sleep(delay)

        raise RuntimeError(f"下载失败 [{url} {start}-{end}]: {last_err}")

    def _probe_size(self, url: str, mirror: Mirror) -> int:
        """探测文件总大小"""
        try:
            from .version import get_short_version
            ua = f"XPM-Suite/{get_short_version()}"
        except ImportError:
            ua = "XPM-Suite/3.1"
        for attempt in range(self.retry):
            try:
                req = Request(url)
                req.add_header("User-Agent", ua)
                req.add_method("HEAD")
                with urlopen(req, timeout=self.timeout) as resp:
                    return int(resp.headers.get("Content-Length", 0))
            except Exception:
                time.sleep(self.backoff_base ** attempt)
        # 回退：GET 第一个字节
        data = self._http_get_range(url, 0, 0, mirror)
        return len(data)

    def download(self, url_path: str, dest: str,
                 expected_sha256: str = "", mirror: Optional[Mirror] = None) -> str:
        """
        下载文件到 dest。
        url_path: 相对路径（如 pool/main/h/htop/htop_3.4.1-5_arm64.deb）
        返回最终文件路径。
        """
        if mirror is None:
            mirror = self.mgr.best()
            if mirror is None:
                raise RuntimeError("没有可用镜像")

        url = mirror.full_url(url_path)

        # 断点续传：检查已有 .part 文件
        part_file = dest + ".part"
        existing_size = 0
        if os.path.exists(part_file):
            existing_size = os.path.getsize(part_file)

        # 探测总大小
        total_size = self._probe_size(url, mirror)
        if total_size <= 0:
            raise RuntimeError(f"无法获取文件大小: {url}")

        # 如果已下载完成，直接重命名
        if existing_size >= total_size and total_size > 0:
            os.replace(part_file, dest)
            return dest

        # 计算分块
        if total_size <= self.chunk_size * 2:
            self.threads = 1  # 小文件不分块

        # 分块：每块大小均匀，最后一块补齐
        chunk_size = total_size // self.threads if self.threads > 0 else total_size
        chunks = []
        for i in range(self.threads):
            start = i * chunk_size
            end = (i + 1) * chunk_size - 1
            if i == self.threads - 1:
                end = total_size - 1
            # 跳过已下载的部分
            if start < existing_size:
                start = max(start, existing_size)
            if start <= end:
                chunks.append((start, end, i))

        # 多线程下载
        results = {}
        lock = threading.Lock()
        downloaded = existing_size

        def worker(start, end, idx):
            nonlocal downloaded
            if start > end:
                results[idx] = b""
                return
            data = self._http_get_range(url, start, end, mirror)
            with lock:
                downloaded += len(data)
                if self._progress_cb:
                    self._progress_cb(downloaded, total_size, f"chunk {idx}")
                # 带宽限制
                if self.bandwidth_limit > 0 and len(data) > 0:
                    expected_time = len(data) / self.bandwidth_limit
                    if expected_time > 0.1:
                        time.sleep(min(expected_time, 1.0))
            results[idx] = data

        threads_list = []
        for start, end, idx in chunks:
            t = threading.Thread(target=worker, args=(start, end, idx))
            threads_list.append(t)
            t.start()

        for t in threads_list:
            t.join()

        # 合并写入：先复制已有数据，再追加新数据
        with open(part_file, "wb") as f:
            # 写入已有的部分（断点续传）
            if existing_size > 0:
                with open(part_file, "rb") as fo:
                    f.write(fo.read(existing_size))
            # 按块顺序写入新下载的数据
            for i in range(self.threads):
                if i in results and results[i]:
                    f.write(results[i])

        # 验证大小
        final_size = os.path.getsize(part_file)
        if final_size != total_size:
            # 大小不匹配，删除并失败
            os.remove(part_file)
            raise RuntimeError(
                f"下载大小不匹配: 期望 {total_size}, 实际 {final_size}"
            )

        # 重命名
        os.replace(part_file, dest)

        # SHA256 校验
        if expected_sha256:
            actual = self._sha256(dest)
            if actual != expected_sha256.lower():
                os.remove(dest)
                raise ValueError(
                    f"SHA256 校验失败: 期望 {expected_sha256}, 实际 {actual}")

        # 记录下载历史
        self._record_history(url, dest, total_size, mirror.name)

        return dest

    def _sha256(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024*1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    def _record_history(self, url: str, dest: str, size: int, mirror: str):
        hist_file = "/var/cache/xpm/download_history.json"
        try:
            os.makedirs(os.path.dirname(hist_file), exist_ok=True)
            history = []
            if os.path.exists(hist_file):
                with open(hist_file) as f:
                    history = json.load(f)
            history.append({
                "url": url, "dest": dest, "size": size,
                "mirror": mirror, "time": time.time(),
            })
            # 只保留最近 100 条
            history = history[-100:]
            tmp = hist_file + ".tmp"
            with open(tmp, "w") as f:
                json.dump(history, f, indent=2)
            os.replace(tmp, hist_file)
        except (PermissionError, OSError):
            pass

    def download_with_failover(self, url_path: str, dest: str,
                               expected_sha256: str = "") -> str:
        """下载 + 镜像故障转移"""
        mirror = self.mgr.best()
        attempts = 0
        max_attempts = len(self.mgr.mirrors)

        while mirror and attempts < max_attempts:
            try:
                return self.download(url_path, dest, expected_sha256, mirror)
            except Exception as e:
                print(f"  ⚠️ [{mirror.name}] 失败: {e}")
                mirror = self.mgr.next_after_failure(mirror)
                attempts += 1

        raise RuntimeError(f"所有镜像都失败了: {url_path}")

    def verify_deb(self, path: str) -> bool:
        """快速校验是否为有效 .deb"""
        try:
            with open(path, "rb") as f:
                header = f.read(8)
            return header == b"!<arch>\n"
        except Exception:
            return False

# === 便捷函数 ===

_default_mgr = None
_default_dl = None

def get_mirror_manager() -> MirrorManager:
    global _default_mgr
    if _default_mgr is None:
        _default_mgr = MirrorManager()
    return _default_mgr

def get_downloader() -> ChunkDownloader:
    global _default_dl
    if _default_dl is None:
        from .config import get_downloader_config
        cfg = get_downloader_config()
        _default_dl = ChunkDownloader(
            mirror_mgr=get_mirror_manager(),
            threads=cfg.get("threads", 4),
            chunk_size=cfg.get("chunk_size", 1048576),
            timeout=cfg.get("timeout", 30),
            retry=cfg.get("retry", 5),
            backoff_base=cfg.get("backoff_base", 2),
            bandwidth_limit=cfg.get("bandwidth_limit", 0),
        )
    return _default_dl

def speedtest(url_path: str = "dists/trixie/Release",
              mirror: Optional[Mirror] = None) -> dict:
    """测速：返回 {mirror, latency_ms, download_mbps}"""
    mgr = get_mirror_manager()
    if mirror is None:
        mirror = mgr.best()
    if mirror is None:
        return {"error": "无可用镜像"}

    url = mirror.full_url(url_path)
    start = time.time()
    try:
        req = Request(url)
        from ..version import get_version_string
        req.add_header("User-Agent", f"XPM-Suite/{get_version_string()}")
        with urlopen(req, timeout=10) as resp:
            data = resp.read(1024*256)  # 读 256KB
        elapsed = time.time() - start
        size_bits = len(data) * 8
        mbps = (size_bits / elapsed) / 1_000_000 if elapsed > 0 else 0
        mirror.latency = elapsed * 1000
        return {
            "mirror": mirror.name,
            "url": mirror.base_url,
            "latency_ms": round(elapsed * 1000, 1),
            "download_mbps": round(mbps, 2),
            "bytes": len(data),
        }
    except Exception as e:
        return {"mirror": mirror.name, "error": str(e)}

def measure_all_mirrors() -> List[dict]:
    """测所有镜像速度"""
    mgr = get_mirror_manager()
    results = []
    for m in mgr.mirrors:
        r = speedtest(mirror=m)
        results.append(r)
    return results

if __name__ == "__main__":
    print("=== 镜像延迟测试 ===")
    results = measure_all_mirrors()
    for r in results:
        if "error" in r:
            print(f"  ❌ {r['mirror']:<15} {r['error']}")
        else:
            print(f"  ✅ {r['mirror']:<15} {r['latency_ms']:>8.1f}ms  "
                  f"{r['download_mbps']:>8.2f} Mbps")

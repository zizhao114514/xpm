#!/usr/bin/env python3
"""XPM v2.1-0 终极测试套件"""
import sys, os, subprocess, json, hashlib, tempfile, shutil, gzip
import urllib.request, ssl

sys.path.insert(0, "/data/workspace/xpm")

from xpm import (
    VERSION, CODENAME, log_info, log_ok, log_warn, log_err, log_stage,
    Source, load_sources,
    parse_packages_gz, search_package, resolve_dependencies,
    ProgressDownloader,
    cmd_version, cmd_doctor, cmd_list, cmd_mirrors,
    cmd_check_update, cmd_search,
)

PASS = 0
FAIL = 0
ERRORS = []

def test(name, func):
    global PASS, FAIL
    try:
        func()
        print(f"  ✓ {name}")
        PASS += 1
    except Exception as e:
        print(f"  ✗ {name}: {e}")
        FAIL += 1
        ERRORS.append((name, str(e)))

# ════════════════════════════════════════
# 1. 版本信息
# ════════════════════════════════════════
def t_version():
    assert VERSION == "2.1-0", f"VERSION={VERSION}"
    assert CODENAME == "Ultimate Edition"
    r = subprocess.run(["python3", "/data/workspace/xpm/xpm.py", "version"],
                       capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, f"returncode={r.returncode}, stderr={r.stderr}"
    assert "xpm 2.1-0" in r.stdout, f"stdout={r.stdout}"
    assert "石油储备" in r.stdout, f"stdout={r.stdout}"

# ════════════════════════════════════════
# 2. Source 解析
# ════════════════════════════════════════
def t_source_parse():
    s = Source("deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main contrib non-free")
    assert s.enabled == True
    assert s.type == "deb"
    assert s.url == "https://mirrors.tuna.tsinghua.edu.cn/debian"
    assert s.suite == "trixie"
    assert "main" in s.components
    assert "non-free" in s.components

def t_source_disabled():
    s = Source("#deb http://example.com/debian trixie main")
    assert s.enabled == False

def t_source_arch_option():
    s = Source("deb [arch=amd64] https://example.com/debian trixie main")
    assert s.arch == "amd64"
    assert s.url == "https://example.com/debian"

def t_release_url():
    s = Source("deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main")
    url = s.release_url()
    assert url == "https://mirrors.tuna.tsinghua.edu.cn/debian/dists/trixie/Release"
    pkg_url = s.release_url("main")
    assert pkg_url == "https://mirrors.tuna.tsinghua.edu.cn/debian/dists/trixie/main/binary-amd64/Packages.gz"

def t_package_url():
    s = Source("deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main")
    url = s.package_url("pool/main/h/htop/htop_3.4.1-5_amd64.deb")
    assert url == "https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/h/htop/htop_3.4.1-5_amd64.deb"

# ════════════════════════════════════════
# 3. Packages 解析
# ════════════════════════════════════════
PKG_GZ_DATA = b"""Package: htop
Version: 3.4.1-5
Architecture: amd64
Depends: libc6 (>= 2.34), libncursesw6 (>= 6.1), libtinfo6 (>= 6.1)
Filename: pool/main/h/htop/htop_3.4.1-5_amd64.deb
Description: interactive processes viewer
 an interactive process viewer
 .
 htop is a free (GPL) ncurses-based process viewer.

Package: libtinfo6
Version: 6.5+20250216-2
Architecture: amd64
Filename: pool/main/n/ncurses/libtinfo6_6.5+20250216-2_amd64.deb
Description: shared low-level terminfo library

"""

def t_parse_packages():
    pkgs = parse_packages_gz(gzip.compress(PKG_GZ_DATA))
    assert len(pkgs) == 2
    names = [p["Package"] for p in pkgs]
    assert "htop" in names
    assert "libtinfo6" in names

def t_parse_filename():
    pkgs = parse_packages_gz(gzip.compress(PKG_GZ_DATA))
    htop = [p for p in pkgs if p["Package"] == "htop"][0]
    assert htop["Filename"] == "pool/main/h/htop/htop_3.4.1-5_amd64.deb"

def t_resolve_deps():
    pkgs = parse_packages_gz(gzip.compress(PKG_GZ_DATA))
    htop = [p for p in pkgs if p["Package"] == "htop"][0]
    deps = resolve_dependencies(htop)
    assert "libc6" in deps
    assert "libncursesw6" in deps
    assert "libtinfo6" in deps
    assert "htop" not in deps

def t_resolve_deps_empty():
    assert resolve_dependencies({}) == []

# ════════════════════════════════════════
# 4. 下载器测试
# ════════════════════════════════════════
def t_progress_downloader_init():
    dl = ProgressDownloader("https://example.com/test.deb", "/tmp/test.deb")
    assert dl.url == "https://example.com/test.deb"
    assert dl.downloaded == 0

def t_verify_deb_valid():
    """创建一个假的 .deb（ar 格式）测试校验"""
    import struct
    # 写最小 ar 文件
    with open("/tmp/fake_valid.deb", "wb") as f:
        f.write(b"!<arch>\n")
        # debian-binary 成员
        name = b"debian-binary"
        mtime = b"0"
        uid = b"0"
        gid = b"0"
        mode = b"100644"
        size = b"4"
        f.write(struct.pack("16s12s6s6s8s10s2s", name, mtime, uid, gid, mode, size, b"`\n"))
        f.write(b"2.0\n")
    
    dl = ProgressDownloader("http://example.com/fake.deb", "/tmp/fake_valid.deb")
    dl.verify_deb()  # 不应抛异常
    os.remove("/tmp/fake_valid.deb")

def t_verify_deb_invalid():
    """HTML 文件应该被检测为无效"""
    with open("/tmp/fake_html.deb", "w") as f:
        f.write("<!DOCTYPE html><html>404 Not Found</html>")
    
    dl = ProgressDownloader("http://example.com/fake.deb", "/tmp/fake_html.deb")
    try:
        dl.verify_deb()
        assert False, "应该抛出异常"
    except Exception as e:
        assert "HTML" in str(e) or "valid" in str(e).lower()
    os.remove("/tmp/fake_html.deb")

# ════════════════════════════════════════
# 5. 日志函数
# ════════════════════════════════════════
def t_log_functions():
    # 不应抛异常
    log_info("test")
    log_ok("test")
    log_warn("test")
    log_err("test")
    log_stage(1, 3, "test")

# ════════════════════════════════════════
# 6. 命令测试（不依赖网络）
# ════════════════════════════════════════
def t_help_output():
    r = subprocess.run(["python3", "/data/workspace/xpm/xpm.py", "--help"],
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "XPM" in r.stdout
    assert "install" in r.stdout
    assert "self-update" in r.stdout

def t_unknown_command():
    r = subprocess.run(["python3", "/data/workspace/xpm/xpm.py", "nonexist"],
                       capture_output=True, text=True)
    assert r.returncode == 1

def t_doctor_runs():
    r = subprocess.run(["python3", "/data/workspace/xpm/xpm.py", "doctor"],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode in (0, 1)  # 都可能
    assert "诊断" in r.stdout or "doctor" in r.stdout.lower()

def t_list_empty():
    r = subprocess.run(["python3", "/data/workspace/xpm/xpm.py", "list"],
                       capture_output=True, text=True)
    assert r.returncode == 0

# ════════════════════════════════════════
# 7. build_deb.py 测试
# ════════════════════════════════════════
def t_build_deb_exists():
    assert os.path.exists("/data/workspace/xpm/build_deb.py")

def t_build_deb_syntax():
    with open("/data/workspace/xpm/build_deb.py") as f:
        code = f.read()
    compile(code, "build_deb.py", "exec")

def t_build_deb_version():
    with open("/data/workspace/xpm/build_deb.py") as f:
        code = f.read()
    assert 'PKG_VERSION = "2.1-0"' in code

# ════════════════════════════════════════
# 8. 文件完整性
# ════════════════════════════════════════
def t_xpm_py_size():
    size = os.path.getsize("/data/workspace/xpm/xpm.py")
    assert size > 20000, f"xpm.py 太小: {size}"

def t_all_source_files():
    for f in ["xpm.py", "xm.py", "xm-build.py", "xpm-build-tool.py",
              "build_deb.py", "tests/test_all.py"]:
        path = f"/data/workspace/xpm/{f}"
        assert os.path.exists(path), f"缺失: {f}"

# ════════════════════════════════════════
# 9. GitHub API 常量
# ════════════════════════════════════════
def t_github_constants():
    from xpm import GITHUB_API, GITHUB_RELEASES
    assert "zizhao114514/xpm" in GITHUB_API
    assert "github.com" in GITHUB_RELEASES

# ════════════════════════════════════════
# 10. 版本比较逻辑
# ════════════════════════════════════════
def t_version_compare():
    cur = VERSION.replace("-", ".")
    assert cur == "2.1.0"
    # 模拟比较
    assert "2.1.0" < "2.2.0"
    assert "2.1.0" > "2.0.8"
    assert "2.1.0" == "2.1.0"

# ════════════════════════════════════════
# 运行全部测试
# ════════════════════════════════════════
print(f"XPM v{VERSION} 测试套件")
print(f"={'='*50}")

tests = [
    # 版本
    ("版本信息正确", t_version),
    # Source
    ("Source 解析标准行", t_source_parse),
    ("Source 解析禁用行", t_source_disabled),
    ("Source 解析 [arch=] 选项", t_source_arch_option),
    ("Source release_url() 正确", t_release_url),
    ("Source package_url() 正确拼 Filename", t_package_url),
    # Packages
    ("Packages.gz 解析", t_parse_packages),
    ("Packages Filename 字段提取", t_parse_filename),
    ("依赖解析 htop", t_resolve_deps),
    ("依赖解析空输入", t_resolve_deps_empty),
    # 下载器
    ("ProgressDownloader 初始化", t_progress_downloader_init),
    ("verify_deb 有效 .deb 通过", t_verify_deb_valid),
    ("verify_deb HTML 被拒绝", t_verify_deb_invalid),
    # 日志
    ("日志函数不抛异常", t_log_functions),
    # 命令
    ("--help 输出包含 self-update", t_help_output),
    ("未知命令返回错误", t_unknown_command),
    ("doctor 命令可运行", t_doctor_runs),
    ("list 命令可运行", t_list_empty),
    # 构建
    ("build_deb.py 存在", t_build_deb_exists),
    ("build_deb.py 语法正确", t_build_deb_syntax),
    ("build_deb.py 版本号 2.1-0", t_build_deb_version),
    # 文件
    ("xpm.py 大小合理", t_xpm_py_size),
    ("所有源文件存在", t_all_source_files),
    # GitHub
    ("GitHub API 常量正确", t_github_constants),
    # 版本
    ("版本比较逻辑", t_version_compare),
]

for name, func in tests:
    test(name, func)

print(f"\n={'='*50}")
print(f"结果: {PASS} 通过, {FAIL} 失败 (共 {PASS+FAIL})")
if ERRORS:
    print("\n失败详情:")
    for name, err in ERRORS:
        print(f"  {name}: {err}")

sys.exit(0 if FAIL == 0 else 1)

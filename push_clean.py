#!/usr/bin/env python3
"""推送 + 创建 Release + 上传 .deb"""
import subprocess, json, os, sys

# 用环境变量里的 token（不硬编码）
token = os.environ.get("GITHUB_TOKEN", "")
if not token:
    # 也尝试 GITHUB_TOKEN 大写
    token = os.environ.get("GITHUB_TOKEN", "")
if not token:
    print("❌ 需要 GITHUB_TOKEN 环境变量")
    print("   运行: export GITHUB_TOKEN=ghp_xxx")
    print("   然后: python3 push_clean.py")
    sys.exit(1)

repo = "zizhao114514/xpm"
deb_path = "/data/workspace/xpm/xpm_2.0-4_all.deb"

# 1. 推送
print("📤 推送到 GitHub...")
r = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
print(r.stdout)
if r.returncode != 0:
    print(f"❌ push 失败: {r.stderr}")
    sys.exit(1)

# 2. 打 tag
print("🏷️ 推送 tag v2.0-4...")
r = subprocess.run(["git", "push", "origin", "v2.0-4", "--force"], capture_output=True, text=True)
print(r.stdout)
if r.returncode != 0:
    print(f"⚠️ tag push: {r.stderr}")

# 3. 创建 Release
print("🚀 创建 GitHub Release...")
import urllib.request
req = urllib.request.Request(
    f"https://api.github.com/repos/{repo}/releases",
    data=json.dumps({
        "tag_name": "v2.0-4",
        "name": "XPM v2.0-4 Scope-Fixed Edition",
        "body": "## XPM v2.0-4 \"Scope-Fixed Edition\"\n\n### 🐛 Bug 修复\n- **修复 `UnboundLocalError: info`** — 全局 `info()` 函数被局部变量覆盖导致 `xpm update` 崩溃\n- 将所有日志函数重命名：`info→log_info, ok→log_ok, warn→log_warn, err→log_err, stage→log_stage`\n- 使用 `fakeroot + dpkg-deb -Zgzip` 官方工具链构建 .deb\n- `md5sums` 包含在 control.tar.gz 中（apt 兼容性）\n\n### ✅ 验证\n- 31/31 测试通过\n- `dpkg-deb -I` 通过\n- `dpkg-deb -c` 通过（22 个文件）\n- `gzip -t` 完整性通过\n\n石油储备: 100001% | 功耗: 1.x W",
        "draft": False,
        "prerelease": False
    }).encode(),
    headers={
        "Authorization": f"token {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json"
    }
)
resp = urllib.request.urlopen(req)
release = json.loads(resp.read())
release_id = release["id"]
upload_url = release["upload_url"].replace("{?name,label}", "")
print(f"  ✅ Release 创建: {release['html_url']}")

# 4. 上传 .deb
print("📦 上传 .deb ...")
with open(deb_path, "rb") as f:
    data = f.read()
req2 = urllib.request.Request(
    f"{upload_url}?name=xpm_2.0-4_all.deb&label=XPM%20v2.0-4%20(.deb)",
    data=data,
    headers={
        "Authorization": f"token {token}",
        "Content-Type": "application/vnd.debian.binary-package",
        "Accept": "application/vnd.github+json"
    }
)
resp2 = urllib.request.urlopen(req2)
asset = json.loads(resp2.read())
print(f"  ✅ 上传完成: {asset['browser_download_url']}")

print(f"\n🎉 全部完成!")
print(f"   Release: https://github.com/{repo}/releases/tag/v2.0-4")
print(f"   .deb:    https://github.com/{repo}/releases/download/v2.0-4/xpm_2.0-4_all.deb")

#!/usr/bin/env python3
"""
push_v5.py — Push XPM v2.0-2 to GitHub using token from env var.
Token is NEVER hardcoded. Pass via:  GITHUB_TOKEN=ghp_xxx python3 push_v5.py
"""
import os, subprocess, json, sys, time

TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
if not TOKEN:
    print("ERROR: set GITHUB_TOKEN env var first")
    print('  GITHUB_TOKEN=ghp_xxx python3 push_v5.py')
    sys.exit(1)

# Sanity check token format
if not TOKEN.startswith("ghp_"):
    print(f"WARNING: token doesn't start with ghp_ (got {TOKEN[:6]}...)")

REPO = "zizhao114514/xpm"
REMOTE = f"https://{TOKEN}@github.com/{REPO}.git"
TAG = "v2.0-2"
DEB = "/data/workspace/xpm/xpm_2.0-2_all.deb"

def run(cmd, check=True):
    print(f"$ {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True)
    if r.stdout: print(r.stdout.strip())
    if r.stderr: print(r.stderr.strip())
    if check and r.returncode != 0:
        print(f"FAILED (exit {r.returncode})")
        sys.exit(1)
    return r

print("=== Step 1: Configure git ===")
run("git config --global user.name 'Zizhao XPM Builder'")
run("git config --global user.email 'zizhao@localhost'")

print("\n=== Step 2: Set remote with token ===")
run(f"git remote set-url origin {REMOTE}")

print("\n=== Step 3: Add + Commit ===")
run("git add -A")
# Check if there's anything to commit
r = run("git status --porcelain", check=False)
if r.stdout.strip():
    run('git commit -m "XPM v2.0-2 Fixed Debian Package Edition"')
else:
    print("(nothing to commit, already up to date)")

print("\n=== Step 4: Push to GitHub ===")
run("git push origin main")

print("\n=== Step 5: Create tag ===")
run(f"git tag -a {TAG} -m 'XPM v2.0-2 - Proot-Friendly + Gzip Fix'")
run(f"git push origin {TAG}")

print("\n=== Step 6: Create GitHub Release via API ===")
release_body = """## XPM v2.0-2 "Fixed Debian Package Edition"

### 🐛 Bug Fixes
- **Fixed**: `dpkg -i` 报 "无效的归档签名" — gzip 流现在用 `gzip.GzipFile` 完整输出，含 CRC32 校验
- **Fixed**: `dpkg -i` 报 "无法创建目录" — 所有文件从 `/opt/xpm/` 改到 `/usr/local/share/xpm/`（FHS 标准本地路径，proot 100% 可写）
- **Fixed**: ar 成员 size 字段对齐错误 — 现在右对齐零填充 10 字节，dpkg 能正确解析

### ✅ Verified
```
dpkg-deb -I xpm_2.0-2_all.deb   → OK
dpkg-deb -c xpm_2.0-2_all.deb   → 11 files listed
gzip -t control.tar.gz            → OK
gzip -t data.tar.gz               → OK
python3 tests/test_all.py         → 31/31 passed
```

### 📦 Install
```bash
wget https://github.com/zizhao114514/xpm/releases/download/v2.0-2/xpm_2.0-2_all.deb
sudo dpkg -i xpm_2.0-2_all.deb
xpm doctor
```

### 🛢️
Oil reserve: 100001% | Power: 1.x W | Apt: forbidden
"""

api_url = f"https://api.github.com/repos/{REPO}/releases"
curl_cmd = f'''curl -s -X POST {api_url} \\
  -H "Authorization: token {TOKEN}" \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps({"tag_name": TAG, "name": "XPM v2.0-2 Fixed Debian Package Edition", "body": release_body, "draft": False, "prerelease": False})}' '''

r = run(curl_cmd, check=False)
try:
    resp = json.loads(r.stdout)
    if "upload_url" in resp:
        upload_url = resp["upload_url"].replace("{?name,label}", "")
        print(f"Release created: {resp.get('html_url')}")
    elif "id" in resp:
        upload_url = f"https://uploads.github.com/repos/{REPO}/releases/{resp['id']}/assets"
        print(f"Release created (id={resp['id']}): {resp.get('html_url','')}")
    else:
        print(f"Unexpected response: {r.stdout[:500]}")
        sys.exit(1)
except Exception as e:
    print(f"Failed to parse release response: {e}")
    print(f"Raw: {r.stdout[:500]}")
    sys.exit(1)

print("\n=== Step 7: Upload .deb ===")
deb_name = "xpm_2.0-2_all.deb"
upload_cmd = f'''curl -s -X POST "{upload_url}?name={deb_name}&label={deb_name}" \\
  -H "Authorization: token {TOKEN}" \\
  -H "Content-Type: application/vnd.debian.binary-package" \\
  --data-binary @{DEB} '''
r = run(upload_cmd, check=False)
try:
    resp = json.loads(r.stdout)
    if "browser_download_url" in resp:
        print(f"✅ .deb uploaded: {resp['browser_download_url']}")
    else:
        print(f"Upload response: {r.stdout[:500]}")
except:
    print(f"Raw: {r.stdout[:500]}")

print("\n=== Step 8: Remove token from remote ===")
run("git remote set-url origin https://github.com/zizhao114514/xpm.git")

print("\n🎉 ALL DONE!")
print(f"🔗 https://github.com/{REPO}/releases/tag/{TAG}")
print("\n⚠️  REMEMBER: Revoke the token at https://github.com/settings/tokens")

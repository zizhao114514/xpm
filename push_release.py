#!/usr/bin/env python3
"""
XPM Suite v3.0.0 推送脚本 (Python 版)
用法:
  GITHUB_TOKEN=ghp_xxx python3 push_release.py
  或编辑下方 TOKEN 变量
"""
import os, sys, json, subprocess, base64

# ⚠️ 填入你的新 fine-grained token
TOKEN = os.environ.get("GITHUB_TOKEN", "ghp_替换为你的新token")

REPO = "zizhao114514/xpm"
TAG = "v3.0.0"
VERSION = "3.0.0"
DEB_FILE = f"xpm-suite_{VERSION}_all.deb"

API = "https://api.github.com"
UPLOAD = "https://uploads.github.com"

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json",
}

def req(method, url, data=None):
    import urllib.request, urllib.error
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  ❌ HTTP {e.code}: {err[:200]}")
        return None

def upload_file(url, filepath):
    """用 PUT 上传文件到 GitHub Releases"""
    import urllib.request, urllib.error
    headers = {
        "Authorization": f"token {TOKEN}",
        "Content-Type": "application/octet-stream",
    }
    with open(filepath, "rb") as f:
        data = f.read()
    r = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  ❌ Upload HTTP {e.code}: {err[:200]}")
        return None

def main():
    print("🚀 XPM Suite 推送脚本 (Python)")
    print(f"   Token: {TOKEN[:10]}...")
    print(f"   Repo:  {REPO}")
    print(f"   Tag:   {TAG}")
    print()

    if "替换" in TOKEN:
        print("❌ 请先设置 GITHUB_TOKEN 环境变量，或编辑脚本中的 TOKEN 变量")
        sys.exit(1)

    # 1. 测试认证
    print("🔑 测试认证...")
    user = req("GET", f"{API}/user")
    if not user or "login" not in user:
        print("❌ Token 认证失败")
        sys.exit(1)
    print(f"  ✅ 认证成功: {user['login']}")

    # 2. 推送代码
    print("\n📤 推送代码...")
    ret = subprocess.run(
        ["git", "push", f"https://{TOKEN}@github.com/{REPO}.git", "master"],
        capture_output=True, text=True
    )
    if ret.returncode != 0:
        print(f"  ⚠️ 推送输出: {ret.stdout[:200]}")
        print(f"  ⚠️ 推送错误: {ret.stderr[:200]}")
    else:
        print("  ✅ 代码推送成功")

    # 3. 推送 tag
    print("\n🏷️  推送 tag...")
    subprocess.run(["git", "tag", TAG], capture_output=True)
    ret = subprocess.run(
        ["git", "push", f"https://{TOKEN}@github.com/{REPO}.git", TAG],
        capture_output=True, text=True
    )
    if ret.returncode == 0:
        print(f"  ✅ Tag {TAG} 推送成功")
    else:
        print(f"  ⚠️ Tag 可能已存在: {ret.stderr[:100]}")

    # 4. 检查/创建 Release
    print("\n📦 创建 Release...")
    existing = req("GET", f"{API}/repos/{REPO}/releases/tags/{TAG}")

    if existing and "id" in existing:
        release_id = existing["id"]
        print(f"  ✅ Release 已存在 (id={release_id})")
    else:
        body = """## XPM Suite v3.0.0 "Add Gui Store Edition"

### 🎉 核心功能
- **xpm** 包管理器：架构探测/依赖解析/多线程下载/事务安装/触发器引擎
- **xstore** 应用商店 CLI：浏览/搜索/热门排行/评分/自定义应用集
- **xstore-gui** 图形应用商店：深色主题/卡片布局/分类侧栏/下载队列
- 支持 .deb 和 .oil 双格式
- 纯 Python 实现，零外部依赖
- 146/146 测试全绿

### 📦 安装
```bash
sudo dpkg -i xpm-suite_3.0.0_all.deb
```

### 🔗 快速开始
```bash
xpm version          # 查看版本
xpm arch             # 架构信息
xpm update           # 更新索引
xstore               # 应用商店
xstore-gui           # 图形界面
```

### ⚠️ Security
用完请 Revoke token: https://github.com/settings/tokens"""
        data = {
            "tag_name": TAG,
            "name": f'XPM Suite v{VERSION} "Add Gui Store Edition"',
            "body": body,
            "draft": False,
            "prerelease": False,
        }
        rel = req("POST", f"{API}/repos/{REPO}/releases", data)
        if not rel or "id" not in rel:
            print("❌ Release 创建失败")
            sys.exit(1)
        release_id = rel["id"]
        print(f"  ✅ Release 创建成功 (id={release_id})")

    # 5. 构建 .deb (如果不存在)
    if not os.path.exists(DEB_FILE):
        print(f"\n📦 构建 {DEB_FILE}...")
        subprocess.run([sys.executable, "build_deb.py"], check=True)

    # 6. 上传 .deb
    print(f"\n⬆️  上传 {DEB_FILE}...")
    upload_url = f"{UPLOAD}/repos/{REPO}/releases/{release_id}/assets?name={DEB_FILE}"
    result = upload_file(upload_url, DEB_FILE)
    if result and "name" in result:
        print(f"  ✅ 上传成功: {result['name']} ({result.get('size',0)/1024:.1f} KB)")
    else:
        print("  ⚠️ 上传失败（可能已存在），继续...")

    # 7. 完成
    print()
    print("🎉🎉🎉 全部完成！🎉🎉🎉")
    print()
    print(f"   📦 Release: https://github.com/{REPO}/releases/tag/{TAG}")
    print(f"   ⬇️  下载:    https://github.com/{REPO}/releases/download/{TAG}/{DEB_FILE}")
    print()
    print("⚠️  记得去 Revoke token: https://github.com/settings/tokens")

if __name__ == "__main__":
    main()

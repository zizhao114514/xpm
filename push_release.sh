#!/bin/bash
# ============================================================
#  XPM Suite v3.0.0 "Add Gui Store Edition" — 一键推送脚本
#  用法: 
#    1. 编辑下方 GITHUB_TOKEN 填入你的新 token
#    2. chmod +x push_release.sh && ./push_release.sh
# ============================================================

# ⚠️ 把这里的 token 换成你的新 fine-grained token
#    创建地址: https://github.com/settings/tokens?type=beta
#    权限: 只给 zizhao114514/xpm  → Contents: Read & Write
GITHUB_TOKEN="${GITHUB_TOKEN:-ghp_替换为你的新token}"

REPO="zizhao114514/xpm"
TAG="v3.0.0"
VERSION="3.0.0"

cd "$(dirname "$0")"

echo "🚀 XPM Suite 推送脚本"
echo "   Token: ${GITHUB_TOKEN:0:10}..."
echo "   Repo:  $REPO"
echo "   Tag:   $TAG"
echo ""

# 1. 检查 token
if [[ "$GITHUB_TOKEN" == *"替换"* ]]; then
    echo "❌ 请先编辑脚本，填入你的 GitHub Token"
    exit 1
fi

# 2. 测试认证
echo "🔑 测试 GitHub 认证..."
AUTH_TEST=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user)
USER_LOGIN=$(echo "$AUTH_TEST" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('login','FAIL'))" 2>/dev/null)
if [[ "$USER_LOGIN" == "FAIL" || -z "$USER_LOGIN" ]]; then
    echo "❌ Token 认证失败，请检查是否过期或权限不足"
    echo "   响应: $AUTH_TEST" | head -3
    exit 1
fi
echo "  ✅ 认证成功: $USER_LOGIN"

# 3. 推送代码
echo ""
echo "📤 推送代码到 GitHub..."
git push "https://${GITHUB_TOKEN}@github.com/${REPO}.git" master 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 代码推送失败（可能仓库不存在或 token 无写权限）"
    exit 1
fi

# 4. 创建 Tag
echo ""
echo "🏷️  创建 Tag $TAG..."
git tag "$TAG" 2>/dev/null || true
git push "https://${GITHUB_TOKEN}@github.com/${REPO}.git" "$TAG" 2>&1
echo "  ✅ Tag 推送完成"

# 5. 创建 Release + 上传 .deb
echo ""
echo "📦 创建 GitHub Release..."

# 检查是否已存在 release
EXISTING=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/repos/${REPO}/releases/tags/${TAG}")
RELEASE_ID=$(echo "$EXISTING" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null)

if [ -z "$RELEASE_ID" ]; then
    # 创建新 release
    CREATE_RESP=$(curl -s -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Content-Type: application/json" \
        "https://api.github.com/repos/${REPO}/releases" \
        -d "{
            \"tag_name\": \"${TAG}\",
            \"name\": \"XPM Suite v${VERSION} Add Gui Store Edition\",
            \"body\": \"## XPM Suite v${VERSION} \\\"Add Gui Store Edition\\\"\\n\\n### 🎉 核心功能\\n- **xpm** 包管理器：架构探测/依赖解析/多线程下载/事务安装/触发器引擎\\n- **xstore** 应用商店 CLI：浏览/搜索/热门排行/评分/自定义应用集\\n- **xstore-gui** 图形应用商店：深色主题/卡片布局/分类侧栏/下载队列\\n- 支持 .deb 和 .oil 双格式\\n- 纯 Python 实现，零外部依赖\\n- 146/146 测试全绿\\n\\n### 📦 安装\\n\\\`\\\`\\\`bash\\nsudo dpkg -i xpm-suite_${VERSION}_all.deb\\n\\\`\\\`\\\`\\n\\n### 🔗 快速开始\\n\\\`\\\`\\\`bash\\nxpm version          # 查看版本\\nxpm arch             # 架构信息\\nxpm update           # 更新索引\\nxstore               # 应用商店\\nxstore-gui           # 图形界面\\n\\\`\\\`\\\`\\n\\n### ⚠️ Security\\n用完请 Revoke token: https://github.com/settings/tokens\",
            \"draft\": false,
            \"prerelease\": false
        }")
    RELEASE_ID=$(echo "$CREATE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null)
fi

if [ -z "$RELEASE_ID" ]; then
    echo "❌ Release 创建失败"
    echo "$CREATE_RESP" | head -5
    exit 1
fi
echo "  ✅ Release 创建成功 (id=$RELEASE_ID)"

# 6. 上传 .deb
echo ""
echo "⬆️  上传 xpm-suite_${VERSION}_all.deb ..."
DEB_FILE="xpm-suite_${VERSION}_all.deb"
if [ ! -f "$DEB_FILE" ]; then
    echo "  ⚠️ $DEB_FILE 不存在，先构建..."
    python3 build_deb.py 2>&1 | tail -5
fi

UPLOAD_URL="https://uploads.github.com/repos/${REPO}/releases/${RELEASE_ID}/assets?name=${DEB_FILE}"
UPLOAD_RESP=$(curl -s -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Content-Type: application/octet-stream" \
    --data-binary @"$DEB_FILE" \
    "$UPLOAD_URL")
UPLOAD_NAME=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name','FAIL'))" 2>/dev/null)

if [[ "$UPLOAD_NAME" == "FAIL" || -z "$UPLOAD_NAME" ]]; then
    echo "❌ 上传失败"
    echo "$UPLOAD_RESP" | head -5
    exit 1
fi
echo "  ✅ 上传成功: $UPLOAD_NAME"

# 7. 完成
echo ""
echo "🎉🎉🎉 全部完成！🎉🎉🎉"
echo ""
echo "   📦 Release 页面: https://github.com/${REPO}/releases/tag/${TAG}"
echo "   ⬇️  下载链接:    https://github.com/${REPO}/releases/download/${TAG}/${DEB_FILE}"
echo ""
echo "⚠️  记得去 Revoke token: https://github.com/settings/tokens"

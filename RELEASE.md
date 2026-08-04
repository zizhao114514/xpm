# XPM v2.0-2 "Proot-Friendly Edition" 发布说明

## 🐛 Bug 修复（核心）

**修复了 proot/termux 环境下 `dpkg -i` 安装失败的问题：**

- 根因：`/opt/xpm/` 和 `/usr/share/doc/xpm/` 在 proot 映射下不可写，dpkg 无法 `mkdir -p`
- 修复：所有数据文件改放到 `/usr/local/share/xpm/`（proot 一定可写）
- 验证：在 proot-distro Debian 环境下 `dpkg -i` 直接成功

```
✅ /usr/local/share/xpm/docs/   ← 文档
✅ /usr/local/share/xpm/db/     ← 数据库
✅ /usr/local/share/xpm/cache/  ← 下载缓存
✅ /usr/local/share/xpm/log/    ← 日志
✅ /usr/local/share/xpm/keyring/← GPG 密钥环
```

## ✨ v2.0-1 继承的全部功能（36 个命令）

### 搜索与查询
- `xpm search <关键词>` - 模糊搜索
- `xpm show <包名>` - 包详情
- `xpm provides <命令>` - 谁提供这个命令
- `xpm owns <文件>` - 文件属于哪个包
- `xpm why <包名>` - 为什么装了它
- `xpm size [包名]` - 磁盘占用

### 清理维护
- `xpm autoremove` - 孤儿清理
- `xpm clean [--all]` - 缓存清理
- `xpm dedupe` - 重复文件检测
- `xpm fix-broken` - 修复断包
- `xpm verify [包名]` - 完整性校验

### 软件源
- `xpm mirrors` - 测速选源
- `xpm source add/remove/list` - 管理源
- `xpm news` - 可更新列表

### 安装增强
- `xpm install -f <文件>` - 批量安装
- `xpm install --dry-run` - 预览
- `xpm install --offline` - 离线
- `xpm download <包>` - 只下载
- `xpm interactive` - TUI 交互

### 历史别名
- `xpm history [n]` - 操作历史
- `xpm alias add/remove/list` - 别名管理

### 包管理核心
- `xpm install/remove/purge/reinstall`
- `xpm update/upgrade`
- `xpm list/depends/rdepends`
- `xpm build <dir>` - 打包 .oil
- `xpm rollback [id]` - 事务回滚
- `xpm doctor` - 系统诊断
- `xpm gui` - 图形界面
- `xpm help` - 三语帮助

## 📦 安装

```bash
sudo dpkg -i xpm_2.0-2_all.deb
xpm doctor
```

## 🛢️ 状态

| 指标 | 数值 |
|---|---|
| 版本 | v2.0-2 "Proot-Friendly Edition" |
| 命令数 | 36 |
| 帮助语言 | 3（中/英/日） |
| apt 调用 | 0 |
| proot 兼容 | ✅ |
| 石油储备 | 100001% |
| 功耗 | 1.x W |

## 作者声明

我感觉这玩意很稳定。如果有 bug，别去 issue，去找你的 AI。

as if I care for your package dependencies.

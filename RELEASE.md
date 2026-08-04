# XPM v2.0-1 "Practical Edition" 发布说明

## 🎯 版本定位

在 v2.0-0 "Complete Edition" 基础上，**全面增强实用性**，加入日常包管理真正需要的功能。

## ✨ 新增功能

### 🔍 搜索与查询（5 个新命令）
- `xpm search <关键词>` - 模糊搜索（匹配包名 + 描述）
- `xpm provides <命令>` - 查找哪个包提供某命令
- `xpm owns <文件路径>` - 反查文件属于哪个包
- `xpm why <包名>` - 为什么安装了它（含历史追溯）
- `xpm size [包名]` - 磁盘占用（无参数则全部排序）

### 🧹 清理维护（5 个新命令）
- `xpm autoremove` - 自动移除孤儿包
- `xpm clean [--all]` - 清理下载缓存
- `xpm dedupe` - 检测重复文件冲突
- `xpm fix-broken` - 修复损坏的包
- `xpm verify [包名]` - 完整性校验

### 🌐 软件源增强（3 个新命令）
- `xpm mirrors` - 测试所有源的速度并推荐最优
- `xpm source add <名> <URL> [dist] [comp]` - 命令行添加源
- `xpm source remove <名>` - 命令行删除源
- `xpm news` - 显示可更新的包（一键升级）

### 💡 体验增强（4 个新命令）
- `xpm install -f <文件>` - 从文件批量安装
- `xpm install --dry-run <包>` - 预览安装（不实际执行）
- `xpm install --offline <包>` - 从本地缓存离线安装
- `xpm download <包>` - 只下载不安装
- `xpm interactive` - 交互式选择安装（TUI 列表）

### 📋 历史与别名（3 个新命令）
- `xpm history [数量]` - 显示安装/卸载历史
- `xpm alias add <名> <命令>` - 自定义别名
- `xpm alias list / remove` - 管理别名

### 🩺 增强版 doctor
- 新增 6 项检查：磁盘空间、X11 会话、TTY、缓存大小、石油储备、功耗
- 自动给出修复建议

### 🌍 三语帮助系统
- 根据 `LANG` 自动切换：中文 / 英文 / 日文
- `xpm help` 按语言显示对应帮助

## 📊 完整命令统计

| 分类 | 数量 |
|---|---|
| 包管理 | 8 个 |
| 搜索查询 | 6 个 |
| 清理维护 | 5 个 |
| 软件源 | 7 个 |
| 历史别名 | 3 个 |
| 其他 | 7 个 |
| **合计** | **36 个命令** |

## 🔧 技术改进

- 依赖解析器增强：OR 关系 + 版本约束 + 循环检测
- 下载进度条：实时百分比 + 速度 + ETA
- 事务回滚：自动快照 + 手动恢复
- GPG 签名校验
- .oil 包构建工具
- GUI 增强：搜索框 + 进度条 + 日志窗

## 📦 安装

```bash
sudo dpkg -i xpm_2.0-1_all.deb
xpm doctor
```

## 🛢️ 状态

| 指标 | 数值 |
|---|---|
| 版本 | v2.0-1 "Practical Edition" |
| 命令数 | 36 |
| 帮助语言 | 3（中/英/日） |
| apt 调用 | 0 |
| 石油储备 | 100001% |
| 功耗 | 1.x W |

## 作者声明

我感觉这玩意很稳定。如果有 bug，别去 issue，去找你的 AI。

as if I care for your package dependencies.

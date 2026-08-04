# XPM - X11 Package Manager

> 石油驱动 | 功耗 1.x W | 零 apt | 全中文 | 实用功能拉满

## 版本: v2.0-1 "Practical Edition"

## 快速安装

```bash
sudo dpkg -i xpm_2.0-1_all.deb
xpm doctor
```

## 核心特性

- ✅ **零 apt 调用** - 纯 wget + dpkg
- ✅ **中文优先** - 根据 LANG 自动切换中/英/日
- ✅ **4 阶段安装输出** - 正在选中 / 正在解压 / 正在设置
- ✅ **3 阶段卸载输出** - 正在寻找 / 正在卸载 / 正在清除
- ✅ **依赖解析** - 支持 OR 关系、版本约束、循环检测
- ✅ **事务回滚** - 安装前自动快照
- ✅ **GPG 签名校验**
- ✅ **GUI 进度条** - Tkinter + 线程化

## 实用功能一览

### 包管理
| 命令 | 说明 |
|---|---|
| `xpm install <包>` | 安装（4 阶段输出） |
| `xpm install -f list.txt` | 批量安装 |
| `xpm install --dry-run <包>` | 预览 |
| `xpm install --offline <包>` | 离线安装 |
| `xpm remove <包>` | 卸载（保留配置） |
| `xpm purge <包>` | 彻底清除 |
| `xpm upgrade` | 升级全部 |
| `xpm download <包>` | 只下载 |

### 搜索与查询
| 命令 | 说明 |
|---|---|
| `xpm search <词>` | 模糊搜索 |
| `xpm show <包>` | 详细信息 |
| `xpm provides <命令>` | 谁提供这个命令 |
| `xpm owns <文件>` | 文件属于哪个包 |
| `xpm why <包>` | 为什么装了它 |
| `xpm size [包]` | 空间占用排序 |

### 清理维护
| 命令 | 说明 |
|---|---|
| `xpm autoremove` | 孤儿清理 |
| `xpm clean [--all]` | 缓存清理 |
| `xpm dedupe` | 重复文件检测 |
| `xpm fix-broken` | 修复损坏包 |
| `xpm verify [包]` | 完整性校验 |

### 软件源
| 命令 | 说明 |
|---|---|
| `xpm sources` | 列出源 |
| `xpm update` | 更新索引 |
| `xpm news` | 可更新列表 |
| `xpm mirrors` | 测速选源 |
| `xpm source add <名> <URL>` | 添加源 |
| `xpm source remove <名>` | 删除源 |

### 历史与别名
| 命令 | 说明 |
|---|---|
| `xpm history [n]` | 安装历史 |
| `xpm alias add <名> <命令>` | 添加别名 |
| `xpm alias list` | 列出别名 |

### 其他
| 命令 | 说明 |
|---|---|
| `xpm interactive` | 交互式选择安装 |
| `xpm doctor` | 系统诊断 |
| `xpm rollback [ID]` | 事务回滚 |
| `xpm build <目录>` | 打包 .oil |
| `xpm gui` | 启动 GUI |

## 彩蛋

```bash
xpm coffee       # 咖啡机状态
xpm petroleum    # 石油储备
xpm piggod       # 猪神祝福
```

## 架构

```
XPM 三层架构:
┌─────────────────────────────────────┐
│  CLI / GUI (xpm.py)               │  ← 用户交互层
├─────────────────────────────────────┤
│  核心引擎 (xpm.py 内部)            │  ← 依赖解析/事务/源管理
├─────────────────────────────────────┤
│  后端 (xm.py)                      │  ← dpkg 调用/校验/快照
└─────────────────────────────────────┘
```

## 文件布局

```
/opt/xpm/
├── db/status.json          # 已装包数据库
├── db/transactions/        # 事务快照
├── db/control/            # 包 control 信息
├── db/files/              # 包文件列表
├── cache/                  # 下载缓存
├── log/history.jsonl       # 操作历史
├── config.json            # 配置文件
├── aliases.json           # 命令别名
└── docs/                  # 文档
```

## 测试

```bash
python3 tests/test_all.py
```

## 铁律

> **XPM 永不调用 apt-get / apt-cache / apt**
> 只用 wget 下载 + dpkg 安装 + 自维护数据库

## 作者声明

我感觉这玩意很稳定。如果有 bug，别去 issue，去找你的 AI。

```
石油储备: 100001%
功耗: 1.x W
as if I care for your package dependencies.
```

## License

石油许可证 v2.0 - 随便用，别怪我。

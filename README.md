# XPM - X11 Package Manager

> **Oil-driven. Apt-forbidden. Language-agnostic backend.**

一个不依赖 apt 的包管理器，用 wget + dpkg + 自研后端管理 Debian 系系统。

## 🛢️ 核心哲学

- **石油驱动**：资源以石油储备百分比计量
- **禁用 apt**：`apt-get` / `apt-cache` 被明确禁止
- **后端语言无关**：Python 后端 (`xm`) + C# 后端 (`xmcs`)，可替换
- **咖啡机崩溃计数**：每次异常都记录，作为系统健康指标

## 📦 安装

```bash
wget https://github.com/zizhao114514/xpm/releases/download/v2.0-0/xpm_2.0-0_all.deb
sudo dpkg -i xpm_2.0-0_all.deb
sudo apt-get install -f -y   # 仅用于修 dpkg 依赖，之后 apt 不再使用
```

## 🚀 快速开始

```bash
sudo -i
xpm sources              # 查看已配置的源
xpm update               # 更新源索引（wget）
xpm search vim           # 搜索
xpm install vim          # 安装（4 阶段输出）
xpm remove vim           # 卸载（3 阶段输出）
xpm upgrade              # 升级全部
xpm gui                  # 启动 GUI
xpm doctor               # 系统诊断
xpm stats                # 统计
```

## 🖥️ CLI 输出示例

### 安装
```
$ xpm install vim
[1/4] 正在选中未安装的软件包：vim
[2/4] 正在选中 vim (2:9.1.0964-1)
[2/4] 正在选中 libtinfo6 (6.4+20230625-2)
[3/4] 正在解压 vim (2:9.1.0964-1)...
[3/4] 正在解压 libtinfo6 (6.4+20230625-2)...
[4/4] 正在设置 vim (2:9.1.0964-1)...
[4/4] 正在设置 libtinfo6 (6.4+20230625-2)...
✅ 安装完成
```

### 卸载
```
$ xpm remove vim
[1/3] 正在寻找与 vim 相关的文件...
[2/3] 正在卸载 vim (2:9.1.0964-1)...
[3/3] 正在清除 vim (2:9.1.0964-1)...
✅ 已彻底清除
```

### 下载进度
```
$ xpm install htop
📥 下载 htop_3.2.2-2_arm64.deb (156KB)
  ████████████████░░░░ 78% | 1.4MB/s | ETA 9s
```

## 📁 源配置

### Debian 风格
```
# /etc/xpm/sources.list.d/tuna.list
deb http://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free
```

### XPM 原生风格
```
# /etc/xpm/sources.list.d/petroleum.list
[xpm]
name=Petroleum Stable
url=http://repo.example.com/dists/stable
type=xpm
enabled=yes
```

## 🔧 打包自己的 .oil 包

```bash
# 目录结构
myprog/
├── usr/bin/myprog
├── usr/share/man/man1/myprog.1
└── xpm/control          ← Package/Version/Architecture/Depends

# 构建
xpm build myprog
# 输出: myprog_1.0_all.oil
```

## 🩺 诊断

```bash
$ xpm doctor
🩺 XPM 系统诊断
⚠️ X11 会话检测到
⚠️ stdin 不是 TTY
⚠️ 检测到代理环境变量
✅ 后端 /usr/local/bin/xmcs 可用
✅ 3 个源已配置
🚫 apt-get / apt-cache 被明确禁止
```

## 📂 目录结构

```
/etc/xpm/                    ← 配置
  sources.list.d/             ← 源定义
  xpm.conf                    ← 全局配置
/var/lib/xpm/                ← 数据库
  status.db                   ← 已安装包（唯一真相源）
  coffee.json                 ← 崩溃计数
  rollback/                   ← 回滚快照
/var/cache/xpm/              ← 缓存
  archives/                   ← 下载的 .deb/.oil
  *-Packages                  ← 源索引
/var/log/xpm/                ← 日志
```

## 🧪 测试

```bash
cd /path/to/xpm
python3 tests/test_all.py
# 36 passed in 0.8s
```

## 📜 完整命令列表

| 命令 | 说明 |
|---|---|
| `xpm help` | 显示帮助 |
| `xpm version` | 显示版本 |
| `xpm sources` | 列出源 |
| `xpm update` | 更新索引 |
| `xpm search <kw>` | 搜索 |
| `xpm info <pkg>` | 包信息 |
| `xpm install <pkg> [...]` | 安装 |
| `xpm remove <pkg> [...]` | 卸载 |
| `xpm purge <pkg> [...]` | 清除（含配置） |
| `xpm upgrade` | 升级全部 |
| `xpm reinstall <pkg>` | 重装 |
| `xpm fix-broken` | 修复中断安装 |
| `xpm depends <pkg>` | 查看依赖 |
| `xpm rdepends <pkg>` | 反向依赖 |
| `xpm list [--installed]` | 列出包 |
| `xpm verify [pkg]` | 校验完整性 |
| `xpm rollback list` | 列出回滚点 |
| `xpm rollback <n>` | 执行回滚 |
| `xpm build <dir>` | 构建 .oil 包 |
| `xpm stats` | 统计信息 |
| `xpm doctor` | 系统诊断 |
| `xpm gui` | 启动 GUI |

## 🏗️ 架构

```
xpm (Python 前端 + GUI)
  │
  ├── search  → 读 /var/cache/xpm/Packages
  ├── install → xm install <file.oil>  (调 dpkg)
  ├── remove  → xm remove <pkg>        (调 dpkg)
  ├── update  → wget <源>/Packages.gz
  ├── upgrade → 比对 Packages vs status.db
  └── build   → tar czf <pkg>.oil

xm (Python 后端)  ←→  xmcs (C# 后端，可互换)
  └── dpkg -i / dpkg -r / dpkg --purge
```

## 🔗 链接

- 仓库: https://github.com/zizhao114514/xpm
- 下载: https://github.com/zizhao114514/xpm/releases/download/v2.0-0/xpm_2.0-0_all.deb
- C# 后端: https://github.com/zizhao114514/xpm/raw/main/xmcs_1.9-0+csharp_all.deb

## ⚠️ 系统要求

- Debian / Ubuntu / 衍生版（或任何有 dpkg 的系统）
- Python 3.8+
- wget
- dpkg
- 不需要 apt

## 🛢️ 彩蛋

```bash
$ xpm stats
📊 XPM 统计
  已安装包: 42
  石油储备: 100001%
  咖啡机崩溃: 300000000042
  运行时间: 1337s
🚫 apt-get / apt-cache 被明确禁止
```

---

> "as if I care for your package dependencies."
>
> ☕ Oil: 100001% | Power: 1.x W

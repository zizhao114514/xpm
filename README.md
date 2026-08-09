# XPM Suite

> 统一包管理器 + 应用商店 — 一个项目，全部搞定

## 🏪 X-Store · 📦 XPM · 🖥️ GUI

XPM Suite 将 **包管理器 (xpm)** 和 **应用商店 (xstore + GUI)** 合并为一个统一项目，版本号完全配合，低版本自动降级功能。

---

## ✨ 功能一览

### 📦 XPM — 包管理器核心

| 功能 | 最低版本 | 说明 |
|---|---|---|
| 基础安装/卸载 | v1.0 | 核心操作 |
| 搜索/索引 | v1.0 | 搜索软件包 |
| 智能架构探测 | v2.0 | dpkg → uname → cpuinfo 三源兜底 |
| 自动更新自身 | v2.0 | `xpm self-update` |
| 下载校验 | v2.0 | ar magic 验证，拒绝 HTML 错误页 |
| 纯 Python ar 解析 | v2.0 | 零外部依赖 |
| 依赖解析 | v2.1 | 支持版本约束 + `\|` 或关系 |
| 镜像自动切换 | v2.2 | 故障转移 + 指数退避 |
| 多线程分块下载 | v2.2 | 断点续传 + 带宽限制 |
| **事务安装** | **v3.0** | **全成 or 全回滚** |
| **触发器引擎** | **v3.0** | **纯 Python 实现** |
| **.oil 原生格式** | **v3.0** | 比 .deb 更简洁高效 |
| **快照/恢复** | **v3.0** | 系统状态随时回滚 |
| 并行安装 | v3.1 | 多包并行，更快 |
| 插件系统 | v4.0 | 可扩展架构 |

### 🏪 X-Store — 应用商店

| 功能 | 最低版本 | 说明 |
|---|---|---|
| 分类浏览 | v2.5 | 6 大分类，美观展示 |
| 搜索应用 | v2.5 | 支持名称/描述/标签 |
| 热门排行 | v2.5 | TOP 10 流行度排序 |
| 评分/评论 | v2.5 | 1-5 星 + 文字评论 |
| 自定义应用集 | v2.5 | 组合多个包为一个"应用" |
| **GUI 图形界面** | **v3.0** | **深色主题 + 卡片瀑布流** |
| 主题系统 | v3.1 | 深色/浅色/OLED/Solarized |

---

## 🚀 快速开始

### 安装

```bash
# 下载 .deb
wget https://github.com/zizhao114514/xpm/releases/latest/download/xpm-suite_3.0-0_all.deb

# 安装
sudo dpkg -i xpm-suite_3.0-0_all.deb
```

### 命令行

```bash
# === XPM 包管理器 ===
xpm version              # 查看版本
xpm arch                 # 架构信息
xpm doctor               # 系统诊断
xpm update               # 更新索引
xpm search htop         # 搜索
xpm info htop           # 包详情
xpm install htop        # 安装
xpm list                 # 已安装
xpm lock htop           # 锁定版本
xpm snapshot create      # 创建快照
xpm snapshot restore id  # 恢复快照
xpm autoremove          # 清理孤儿
xpm mirrors              # 镜像测速
xpm speedtest           # 网络测速

# === X-Store 应用商店 CLI ===
xstore                  # 浏览分类
xstore top              # 热门排行
xstore search git       # 搜索
xstore info htop        # 应用详情
xstore install htop     # 一键安装
xstore rate htop 5 太好用了  # 评分
xstore installed        # 已安装
xstore add mydev git,vim,python3 开发环境  # 自定义

# === X-Store GUI ===
xstore-gui              # 启动图形界面
```

### GUI 界面

```
┌──────────────────────────────────────────────────────┐
│ 🏪 X-Store              🔍 [搜索应用...]  🎨 🔥 TOP │
├────────┬─────────────────────────────────────────────┤
│ ⚙️ 系统 │ ⭐ 热门推荐                               │
│ 💻 开发 │ ┌──────┐ ┌──────┐ ┌──────┐            │
│ 🌐 网络 │ │ htop │ │ btop │ │ neof │ ...        │
│ 🎵 多媒体│ └──────┘ └──────┘ └──────┘            │
│ 🔒 安全 │                                         │
│ 🎮 娱乐 │ 📦 全部应用                             │
│        │ ┌──────┐ ┌──────┐ ┌──────┐            │
│        │ │ curl │ │ ffmpeg│ │ vim  │ ...        │
│        │ └──────┘ └──────┘ └──────┘            │
├────────┴─────────────────────────────────────────────┤
│ ✅ htop 安装完成                          ████████ 80%│
└──────────────────────────────────────────────────────┘
```

---

## 🏗️ 项目结构

```
xpm-suite/
├── pyproject.toml          # Python 项目配置
├── build_deb.py            # .deb 构建脚本
├── README.md
├── .github/workflows/
│   └── release.yml        # CI/CD 自动构建 + 发布
├── packaging/
│   ├── tuna.list          # 默认软件源
│   └── xstore-gui.desktop # 桌面入口
├── src/xpm_suite/
│   ├── __init__.py        # 版本 + 功能开关
│   ├── version.py         # 版本管理
│   ├── feature_flags.py   # 功能开关（版本不达标自动禁用）
│   ├── cli/
│   │   └── xpm_main.py   # xpm 命令入口
│   ├── core/
│   │   ├── config.py      # 配置管理
│   │   ├── statusdb.py    # 状态数据库
│   │   ├── downloader.py  # 多线程下载器
│   │   ├── installer.py   # 核心安装引擎
│   │   ├── transaction.py # 事务管理
│   │   ├── triggers.py    # 触发器引擎
│   │   └── scripts_env.py # maintainer scripts 环境
│   ├── formats/
│   │   ├── ar.py          # ar 归档解析
│   │   ├── untar.py       # tar 解压（多格式）
│   │   ├── deb.py         # .deb 解析
│   │   └── oil.py         # .oil 原生格式
│   └── store/
│       ├── __init__.py
│       ├── catalog.py      # 应用目录
│       ├── cli.py          # xstore 命令
│       └── gui/
│           ├── theme.py    # 主题系统
│           ├── store_gui.py # GUI 核心逻辑
│           └── app.py      # tkinter 主窗口
└── tests/
    ├── test_version.py     # 版本/功能开关测试
    ├── test_core.py       # 核心模块测试
    ├── test_formats.py    # 格式解析测试
    ├── test_store.py      # 应用商店测试
    └── test_integration.py # 集成测试
```

---

## 🔧 .oil 包格式

XPM Suite 引入全新的 `.oil` 包格式，比 .deb 更简洁：

```yaml
# oil-manifest.json（每个 .oil 包必有）
name: htop
version: 3.4.1-5
arch: arm64
format: oil-1.0
depends:
  - ["libncursesw6 (>= 6.5)"]
  - ["libtinfo6 (>= 6.5)"]
triggers:
  interest: []
  activate: []
files:
  - usr/bin/htop
  - usr/share/man/man1/htop.1.gz
checksums:
  manifest: sha256...
```

构建 .oil 包：

```python
from xpm_suite.formats.oil import build_oil_package

build_oil_package(
    name="mytool", version="1.0-0", arch="arm64",
    source_dir="./mytool_files/",
    output_path="./mytool.oil",
    description="My awesome tool",
)
```

---

## 🎨 主题系统

X-Store GUI 内置 4 套主题，随时切换：

| 主题 | 特点 |
|---|---|
| 🌙 Dark（默认） | 深蓝底 + 珊瑚红强调，专业大方 |
| ☀️ Light | 浅色明亮，适合白天 |
| 🖤 OLED | 纯黑底，省电护眼 |
| 🟡 Solarized | 经典配色，长时间不累 |

```python
from xpm_suite.store.gui.theme import THEMES, get_theme

t = get_theme("oled")
print(t["bg"], t["accent"])
```

---

## 📋 版本策略

XPM Suite 使用**统一版本号**，功能按版本解锁：

```
v1.x ─── 基础安装/卸载/搜索
  │
v2.x ─── 架构探测 + 多线程下载 + xstore CLI
  │
v3.0 ─── 🎯 当前版本
  │     • 事务安装（全成/全回滚）
  │     • 触发器引擎
  │     • .oil 原生格式
  │     • X-Store GUI
  │
v3.1 ─── 并行安装 + 主题系统
  │
v4.0 ─── 插件系统
```

低版本运行时，高级功能**自动禁用并提示升级**，不会崩溃。

---

## 🧪 运行测试

```bash
cd xpm-suite
python -m pytest tests/ -v
```

---

## 📄 License

MIT License

---

## 🔗 相关链接

- GitHub: https://github.com/zizhao114514/xpm
- Issues: https://github.com/zizhao114514/xpm/issues
- Releases: https://github.com/zizhao114514/xpm/releases

---

**🛢️ 石油储备 100001% | 功耗 0.9 W | XPM Suite — 一个项目搞定一切**
<!-- ci: workflow added -->

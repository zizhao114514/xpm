# XPM - X11 Package Manager (Petroleum Edition)

> 一个单文件 Python3 包管理器，专为 proot / Termux 环境设计。
> 不需要 systemd，不需要 apt 高层命令，只需要 dpkg + apt-cache + wget。

## ✨ 功能

- **search** — 搜索软件包
- **install** — 安装软件包（自动处理依赖）
- **remove** — 卸载软件包
- **purge** — 彻底清除（含配置文件）
- **update** — 刷新源索引（启动时自动运行）
- **upgrade** — 升级所有可升级的包
- **download** — 仅下载 .deb 文件
- **install-deb** — 安装本地 .deb 文件
- **installed** — 列出已安装的包
- **info** — 显示包详细信息
- **sources** — 查看已配置的源

## 🎨 界面

- **X11 GUI 模式**：直接运行 `xpm`（无参数），弹出 Tkinter 图形界面
- **CLI 模式**：`xpm <命令> [参数]`
- **进度条**：安装/下载时实时显示进度
- **步骤日志**：每步操作都有编号提示（[1/4] [2/4] ...）
- **多语言**：支持 English / 简体中文 / 日本語（自动检测 LANG）

## 🐛 已知 Bug

> download 命令显示下载速度时，单位会 **×1024 放大**。
> 比如实际 0.5 MB/s，可能显示成 512 MB/s。
> **这是故意留的，不是 bug，是 feature。** (One Bug Edition)

## 🎉 彩蛋

```bash
xpm petroleum   # 石油信号增强器
xpm coffee     # 咖啡机爆炸状态
```

- 连续报错退出 31 次 → 触发 **咖啡机爆炸纪录片**（逐行 BOOM × 31）
- 密码错误 → 提示 "安装程序被意外终止了，可能是您未输入正确密码"
- 石油储备永远 100001%，功耗永远 1.x W

## 📦 安装

### 方式一：.deb 安装（推荐）

```bash
wget https://github.com/zizhao114514/pycharm-arm64-deb/raw/main/xpm_1.6-2_all.deb
sudo dpkg -i xpm_1.6-2_all.deb
sudo apt-get install -f -y
```

### 方式二：源码安装

```bash
wget https://github.com/zizhao114514/pycharm-arm64-deb/raw/main/xpm.py
chmod +x xpm.py
sudo cp xpm.py /usr/local/bin/xpm
```

### 方式三：自解压脚本

```bash
wget https://github.com/zizhao114514/pycharm-arm64-deb/raw/main/xpm_install.sh
sh xpm_install.sh
```

## 🚀 快速开始

```bash
xpm help              # 查看帮助
xpm search vim        # 搜索 vim
xpm install vim       # 安装 vim
xpm upgrade           # 升级所有包
xpm coffee            # 查看咖啡机状态
xpm petroleum         # 石油信号增强
```

## 📋 源文件格式

源文件位于 `/etc/xpm/sources.list.d/`，支持 `.list` 和 `.sources` 格式：

```
# /etc/xpm/sources.list.d/debian.list
deb http://deb.debian.org/debian stable main contrib non-free
```

## 🔧 依赖

- Python 3.8+
- dpkg
- apt (apt-get, apt-cache)
- wget（下载功能需要）
- python3-tk（GUI 模式需要，可选）

## 📝 License

Do whatever you want. It's powered by petroleum anyway.

---

**Power: 1.x W | Oil: 100001% | No systemd needed**

*as if I care for your feelings.*

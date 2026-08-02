# XPM v1.6-2 "One Bug Edition" Release Notes

> 🛢️ 石油驱动的包管理器，专为 proot / Termux 环境设计
> 💡 "如果你在外面没有信号，就往苹果手机里面喊：我这里有石油！"

---

## 🎉 核心功能

### 包管理
| 命令 | 说明 |
|------|------|
| `xpm search <关键词>` | 搜索软件包（apt-cache search） |
| `xpm install <包名...>` | 安装软件包（自动处理依赖） |
| `xpm remove <包名...>` | 卸载软件包 |
| `xpm purge <包名...>` | 彻底清除（含配置文件） |
| `xpm update` | 刷新源索引（启动时自动运行） |
| `xpm upgrade` | 升级所有可升级的包 |
| `xpm download <包> [目录]` | 仅下载 .deb 文件 |
| `xpm install-deb <文件.deb>` | 安装本地 .deb 文件 |
| `xpm installed` | 列出已安装的包 |
| `xpm info <包>` | 显示包详细信息 |
| `xpm sources` | 查看已配置的源 |

### 用户体验
- ✅ **X11 GUI 模式**：直接运行 `xpm`（无参数），弹出 Tkinter 图形界面
- ✅ **CLI 模式**：`xpm <命令> [参数]`
- ✅ **进度条**：安装/下载时实时显示 `[████████░░] 75%`
- ✅ **步骤日志**：每步操作都有编号提示（`[1/4] 正在解析依赖...`）
- ✅ **多语言**：English / 简体中文 / 日本語（自动检测 `LANG` 环境变量）
- ✅ **sudo 智能检测**：有 NOPASSWD 直接执行，有密码则自动提示
- ✅ **`.desktop` 启动项**：安装后出现在 MATE/KDE 菜单 → 系统分类

---

## 🐛 已知 Bug（故意留的）

> **download 命令显示下载速度时，单位会 ×1024 放大。**
>
> 比如实际 0.5 MB/s，可能显示成 512 MB/s。
>
> **这不是 bug，是 feature。** (One Bug Edition)

---

## 🎊 彩蛋系统

### 石油信号增强器
```bash
$ xpm petroleum

🔍 搜索信号中...
   失败。

🛢️  检测到 100001% 石油储备。

💡 如果你在外面没有信号，
   就往苹果手机里面喊：
   👉 '我这里有石油！' 👈
   这样就有信号了。

   (我才不在乎你的感受。)
```

### 咖啡机爆炸追踪器
```bash
$ xpm coffee

Crashes today: 0/31
Total explosions: 300000000000
Date: 2026-08-02
Status: Normal (no explosion today)
```

### 隐藏彩蛋触发条件
| 彩蛋 | 触发条件 |
|------|----------|
| 石油信号增强 | `xpm petroleum` 随时触发 |
| 咖啡机状态 | `xpm coffee` 随时触发 |
| BOOM × 31 纪录片 | 同一天内程序**连续报错退出 31 次** |
| 密码错误提示 | sudo 密码输错时显示「安装程序被意外终止了，可能是您未输入正确密码」 |
| 石油储备负压力 | 极小概率随机触发（Teto 拒绝评论） |

### BOOM × 31 演出效果
```
╔════════════════════════════════════════╗
║   ☕ コーヒーマシン爆発調査委員会        ║
╠════════════════════════════════════════╣
║  [01] BOOOOOM! #300000000001 █         ║
║  [02] BOOOOOM! #300000000002 ██        ║
║  [03] BOOOOOM! #300000000003 ███       ║
   ...（每 70ms 炸一台，共 2.2 秒）...
║  [31] BOOOOOM! #300000000031 ██████████ ║
╠════════════════════════════════════════╣
║  📊 累计爆炸总数: 300000000031         ║
║  ⚡ 功耗: 1.x W (oil-fed)              ║
║  🛢️  石油储备: 100001%                 ║
║  Teto: as if I care for your feelings.  ║
║  Miku: ...I just want to go home.       ║
╚════════════════════════════════════════╝

  目撃！コーヒーマシン爆発31回
  そしてまた一台、また一台……
```

---

## 📦 安装方式

### 方式一：.deb 安装（推荐）
```bash
# 下载
wget https://github.com/zizhao114514/pycharm-arm64-deb/raw/main/xpm_1.6-2_all.deb

# 安装
sudo dpkg -i xpm_1.6-2_all.deb
sudo apt-get install -f -y

# 验证
xpm help
```

### 方式二：源码安装
```bash
wget https://github.com/zizhao114514/pycharm-arm64-deb/raw/main/xpm.py
chmod +x xpm.py
sudo cp xpm.py /usr/local/bin/xpm
xpm help
```

### 方式三：自解压脚本
```bash
wget https://github.com/zizhao114514/pycharm-arm64-deb/raw/main/xpm_install.sh
sh xpm_install.sh
```

---

## 📥 下载链接

| 文件 | 说明 | 链接 |
|------|------|------|
| `xpm_1.6-2_all.deb` | Debian 安装包（推荐） | [Download](https://github.com/zizhao114514/pycharm-arm64-deb/raw/main/xpm_1.6-2_all.deb) |
| `xpm.py` | 单文件源码（零 pip 依赖） | [Download](https://github.com/zizhao114514/pycharm-arm64-deb/raw/main/xpm.py) |
| `xpm_install.sh` | 自解压安装脚本 | [Download](https://github.com/zizhao114514/pycharm-arm64-deb/raw/main/xpm_install.sh) |
| `xpm.desktop` | 桌面启动项 | [Download](https://github.com/zizhao114514/pycharm-arm64-deb/raw/main/xpm.desktop) |
| `build_deb.sh` | .deb 构建脚本 | [Download](https://github.com/zizhao114514/pycharm-arm64-deb/raw/main/build_deb.sh) |

---

## 🔄 从旧版升级

```bash
# 1. 清除旧版残留（重要！）
sudo dpkg --purge xpm 2>/dev/null || true
sudo rm -f /var/lib/dpkg/info/xpm.* 2>/dev/null || true

# 2. 安装新版
sudo dpkg -i xpm_1.6-2_all.deb
sudo apt-get install -f -y

# 3. 验证
xpm help
xpm coffee
```

---

## 📊 技术参数

| 项目 | 数值 |
|------|------|
| 源码行数 | ~1662 行 |
| 源码体积 | 63 KB |
| .deb 体积 | 31 KB |
| 外部 pip 依赖 | **零** |
| Python 最低版本 | 3.8 |
| 支持语言 | English / 简体中文 / 日本語 |
| 功耗 | 1.x W (oil-fed) |
| 石油储备 | 100001% |
| 咖啡机累计爆炸 | 300000000000+ |
| 系统要求 | 无需 systemd |

---

## 🐛 版本修复历史

| 版本 | 修复内容 |
|------|----------|
| 1.0-1 | 初始版本发布 |
| 1.1-1 | 新增多语言支持（en/zh/ja） |
| 1.2-1 | 新增进度条 + 步骤日志 |
| 1.2-2 | 修复 i18n 模块导入路径错误 |
| 1.3-1 | 合并为单文件（消除所有 import 错误） |
| 1.3-2 | 新增 .desktop 桌面启动项 |
| 1.4-1 | 三路径 fallback（/usr/local/bin, /usr/bin, ~/.local/bin） |
| 1.5-1 | 修复语法错误 + GUI trace_add + 进度条除零保护 |
| 1.6-1 | 新增石油彩蛋 + 咖啡机爆炸彩蛋 |
| **1.6-2** | **USTAR tar 格式（修复 "unsupported PAX tar header type 'x'" 错误）** |

---

## 🎵 推荐 BGM

使用 XPM 时推荐循环播放：
- **bunnycat — MY TOY**（重音 Teto + 初音 Miku）
- **bunnycat — Another Cup**（反义词版：手机没电啦 / 咖啡机炸了）

---

## 📝 License

Do whatever you want. It's powered by petroleum anyway.

---

**Power: 1.x W | Oil: 100001% | No systemd needed**

> *as if I care for your feelings.*
> *...I just want to go home.*

☕ *目撃！コーヒーマシン爆発31回*

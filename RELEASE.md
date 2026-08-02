# XPM v1.7-1 - One Bug Edition (Crash Counting Fix)

> 🛢️ Petroleum-powered package manager for proot/Termux
> 💡 "如果你在外面没有信号，就往苹果手机里面喊：我这里有石油！"

## 🎉 What's New in v1.7-0

### 🐛 GUI Fix (Critical)
- **Fixed `UnboundLocalError: cannot access local variable 'do_search'`**
- Root cause: function definitions were placed AFTER `make_btn()` calls in `gui_mode()`
- Fix: moved ALL function definitions (`do_search`, `do_install`, `do_remove`, `do_purge`, `do_update`, `do_upgrade`, `do_info_btn`, `show_petroleum`, `show_coffee`, `set_status`, `get_selected`) BEFORE button creation
- GUI now launches cleanly with `xpm` (no arguments)
- Affected users: anyone running `xpm` to enter GUI mode got traceback before this fix

### Core Features
- ✅ Full CLI + X11 GUI (Tkinter) dual mode
- ✅ Multi-language support: English / 简体中文 / 日本語
- ✅ Progress bars with real-time apt output parsing
- ✅ Step logging (`[1/4]` style) for all operations
- ✅ `.desktop` entry — appears in MATE/KDE menu
- ✅ Auto-update on launch (runs `apt-get update` silently)
- ✅ sudo password detection (no password prompt if NOPASSWD)
- ✅ USTAR tar format (compatible with old dpkg)

### Easter Eggs
- 🛢️ `xpm petroleum` — Petroleum signal booster
  > 如果你在外面没有信号，就往苹果手机里面喊："我这里有石油！" 这样就有信号了。
- ☕ `xpm coffee` — Coffee machine explosion tracker (300000000000+ explosions)
- 💥 31 consecutive crashes → BOOM × 31 cinematic sequence
  ```
  ╔════════════════════════════════════════╗
  ║  ☕ コーヒーマシン爆発調査委員会              ║
  ╠════════════════════════════════════════╣
  ║  [01] BOOOOOM! #300000000001 █           ║
  ║  ...                                        ║
  ║  [31] BOOOOOM! #300000000031 ████████████ ║
  ╠════════════════════════════════════════╣
  ║  Teto: 我才不在乎你的感受。                 ║
  ║  Miku: ...我只想回家。                    ║
  ╚════════════════════════════════════════╝
  ```
- 🔒 Password error → "安装程序被意外终止了，可能是您未输入正确密码"
- 🎵 Plays well with bunnycat's MY TOY (OpenSL ES pipeline)

### Known Bug (Feature)
- Download speed display is **×1024** of actual speed
- e.g. 0.5 MB/s real → displays as 512 MB/s
- This is intentional. Don't fix it.

## 📦 Installation

### Method 1: .deb package (Recommended)

```bash
# Download
wget https://github.com/zizhao114514/xpm/raw/main/xpm_1.7-0_all.deb

# Install
sudo dpkg -i xpm_1.7-0_all.deb
sudo apt-get install -f -y

# Verify
xpm help
```

### Method 2: Source copy

```bash
wget https://github.com/zizhao114514/xpm/raw/main/xpm.py
chmod +x xpm.py
sudo cp xpm.py /usr/local/bin/xpm
xpm help
```

### Method 3: Self-extract installer

```bash
wget https://github.com/zizhao114514/xpm/raw/main/xpm_install.sh
sh xpm_install.sh
```

## 📥 Download Links

| File | Description | Link |
|------|-------------|------|
| **xpm_1.7-0_all.deb** | Debian package (recommended, 31KB) | [Download](https://github.com/zizhao114514/xpm/raw/main/xpm_1.7-0_all.deb) |
| xpm.py | Single-file source (64KB, 1664 lines) | [Download](https://github.com/zizhao114514/xpm/raw/main/xpm.py) |
| xpm_install.sh | Self-extract installer | [Download](https://github.com/zizhao114514/xpm/raw/main/xpm_install.sh) |
| xpm.desktop | Desktop entry file | [Download](https://github.com/zizhao114514/xpm/raw/main/xpm.desktop) |
| build_deb.sh | Build script for .deb | [Download](https://github.com/zizhao114514/xpm/raw/main/build_deb.sh) |
| install.sh | Install script | [Download](https://github.com/zizhao114514/xpm/raw/main/install.sh) |

## 🔄 Upgrade from Previous Version

```bash
# Clean old residue first (IMPORTANT!)
sudo dpkg --purge xpm 2>/dev/null || true
sudo rm -f /var/lib/dpkg/info/xpm.* 2>/dev/null || true

# Install new version
sudo dpkg -i xpm_1.7-0_all.deb
sudo apt-get install -f -y
```

## 📊 Stats

- Single Python file: ~1664 lines / 64KB
- Zero pip dependencies (only stdlib + tkinter optional)
- .deb size: 31KB
- Languages: en / zh / ja
- Power draw: 1.x W (oil-fed)
- Oil reserve: 100001%
- Coffee machines exploded: 300000000000+

## 🐛 Bugfix History

| Version | Fixes |
|---------|-------|
| 1.0-1 | Initial release |
| 1.1-1 | Added multi-language (en/zh/ja) |
| 1.2-1 | Added progress bars + step logging |
| 1.2-2 | Fixed i18n import path |
| 1.3-1 | Merged to single file (zero import errors) |
| 1.3-2 | Added .desktop entry |
| 1.4-1 | Triple-path fallback (/usr/local/bin, /usr/bin, ~/.local/bin) |
| 1.5-1 | Fixed all syntax errors + GUI trace_add + progress bar div-by-zero |
| 1.6-1 | Added petroleum + coffee easter eggs |
| 1.6-2 | USTAR tar format (fixes "unsupported PAX tar header type 'x'") |
| **1.7-0** | **Fix GUI UnboundLocalError (function defs moved before make_btn calls)** |

## 🎵 Soundtrack

Recommended listening while using XPM:
- bunnycat — MY TOY (重音 Teto + 初音 Miku)
- bunnycat — Another Cup (反义词版: 手机没电啦 / 咖啡机炸了)

---

**as if I care for your feelings.**

**...I just want to go home.**

☕ *目撃！コーヒーマシン爆発31回*

# XPM - X11 Package Manager (Petroleum Edition)

> **Author:** I feel this thing is quite stable.
> If you encounter any bugs, don't create an issue. Just ask your AI.
> 我感觉这玩意很稳定。如果有 bug，别去 issue，去找你的 AI。
> これは安定していると思います。バグがある場合は、問題を起こすのではなく、自分の AI に頼ってください。

## Architecture

```
xpm (frontend) ──calls──▶ xm (backend)
     │                              │
     │ search/install/remove         │ unpack/install/remove/verify
     │ update/upgrade/download      │ lock management
     │ progress bar / i18n / GUI    │ status.db / coffee.log
     │                              │
     └── sudo + apt-cache + wget ──┘
```

## Directory Layout

```
软件包/
├── xpm/
│   ├── control              # Package metadata (key=value format)
│   ├── pmdel/               # Removal scripts
│   │   ├── prerm
│   │   └── postrm
│   ├── pmadd/               # Installation scripts
│   │   ├── preinst
│   │   └── postinst
│   ├── files.list           # File manifest
│   └── checksums.sha256     # Integrity check
│
├── 程序安装目录及文件/        # Destination mapping
├── var/lib/xm/status.json  # Installed package DB
├── var/cache/xm/lock/      # Lock files
└── tmp/xpm-unpack/          # Temp unpack dir
```

## Install

```bash
# .deb
sudo dpkg -i xpm_1.8-0_all.deb
sudo apt-get install -f -y

# Or source
chmod +x install.sh && ./install.sh
```

## Commands

```
update                     Refresh source index (auto on launch)
upgrade                    Upgrade all upgradable packages
search <keyword>          Search packages
install <pkg...>          Install package(s)
remove  <pkg...>          Remove package(s)
purge   <pkg...>          Purge with config
download <pkg> [dir]      Download .deb only
install-deb <file.deb/oil>  Install local .deb or .oil
installed                List installed packages
info    <pkg>             Show package details
sources                 List configured sources
coffee                    Coffee machine status
petroleum                 Petroleum signal booster
help                      Show this help
```

## Known Bug (Intentional, Don't Fix)

- Download speed is shown ×1024 (petroleum unit conversion error)

## Coffee Machine

The coffee machine counts crashes. When it reaches 31 in a day, it plays the BOOM × 31 sequence.

## Backend: xm

`xm` is the autonomous backend. It does NOT use apt/dpkg for package logic:

```
xm unpack   <file.oil> [--root /path]   # Extract to temp
xm install  <file.oil>                   # Full install
xm remove   <pkgname>                    # Full removal
xm query    [pkgname]                    # Query status
xm files    <pkgname>                    # List package files
xm verify   <pkgname>                    # Checksum verify
xm rebuild-db                             # Rebuild status DB
xm coffee                                   # Coffee machine status
```

## Requirements

- python3 >= 3.8
- dpkg, apt (for repo access)
- python3-tk (optional, for GUI mode)
- wget (optional, for downloads)

## Notes

This package manager does not follow FHS. It follows the Petroleum Hierarchy Standard (PHS).
If you expected `/var/lib/dpkg/`, you are in the wrong universe.
If you expected `/etc/apt/`, the coffee machine has already exploded.

**Stable: probably.**

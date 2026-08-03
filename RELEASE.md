# XPM v1.9-0 - "No-Apt Edition" + C# Special Edition

## Highlights

- **Zero apt**: no `apt-get`, no `apt-cache` anywhere in the codebase
- **Dual-format sources**: Debian-style `deb http://...` AND XPM-style `[xpm] url=...`
- **New backend `xm`**: autonomous unpack/install/remove engine
- **Lock file system**: `/var/cache/xm/lock/` with flock + timeout
- **Transaction state machine**: pending → running → committed → done
- **`.oil` package format** support (via xm backend)
- **Directory hierarchy**: 软件包/xpm/pmadd/pmdel/程序安装目录及文件/
- **Coffee machine integration**: crash counting across frontend + backend
- **i18n**: en / zh / ja (author statements in all 3 languages)

## Architecture

```
xpm (frontend, CLI + GUI)
  ├── search / install / remove / purge
  ├── update / upgrade / download
  ├── progress bar + step logging
  ├── i18n (en/zh/ja)
  └── calls xm for low-level ops

xm (backend, oil-powered unpacker)
  ├── unpack / install / remove
  ├── verify (sha256)
  ├── lock management (flock)
  ├── transaction state machine
  └── status.db (yaml)
```

## Lock File Behavior

When a backend operation is in progress, subsequent xpm/xm processes will see:

```
检测到锁文件 (/var/cache/xm/lock/install.lock)
  归属进程: xm (PID 1337)
  操作类型: install xpm
  已等待: 7s
  最大等待: 120s
  状态: unpacking

⏳ 等待锁释放中...
```

On timeout:
```
⚠️ 安装进程无响应。
☕ 咖啡机因等待超时爆炸 +1
🛢️ 石油消耗：0.01%
[今日崩溃次数: 12/31]
```

## C# Special Edition (xmcs)

A complete C# rewrite of the XPM backend is available in the `xpm-csharp/` directory.

| File | Description |
|---|---|
| `src/Program.cs` | Main entry & command dispatch |
| `src/Xm.cs` | Core backend (install/remove/verify/query) |
| `src/LockFile.cs` | Advisory file locking |
| `src/OilPackage.cs` | .oil package parser |
| `src/Transaction.cs` | Transaction state machine |
| `src/Coffee.cs` | Shared crash counter |
| `src/DpkgWrapper.cs` | dpkg wrapper (only external PM call) |
| `build.sh` | Multi-compiler build (dotnet/mcs/csc) |
| `pack_deb.py` | ar-format .deb construction |

### Download
- Binary .deb: `xmcs_1.9-0+csharp_all.deb`
- Source .zip: `xpm-csharp_1.9-0+csharp.zip`

### Install
```bash
sudo dpkg -i xmcs_1.9-0+csharp_all.deb
sudo apt-get install -f -y   # installs mono-runtime if missing
xmcs version
```

### Key Features
- **Zero apt** (only dpkg + tar + wget)
- **Drop-in replacement** for Python `xm` backend
- **Same locks, same database, same .oil format**
- Compiles with Mono `mcs`, Microsoft `csc`, or `dotnet` SDK
- Proves the XPM architecture is **language-agnostic**

## Known Bug (Intentional, Don't Fix)

| Bug | Description |
|---|---|
| Download speed ×1024 | Shown in MB/s but actually KB/s. Petroleum unit conversion. |

## Bugfix History

| Version | Fix |
|---|---|
| 1.0-0 | Initial release, basic CLI |
| 1.3-1 | Single-file, zero import errors |
| 1.4-1 | Three-path fallback for /usr/local/bin |
| 1.6-2 | USTAR tar format (no PAX type-x error) |
| 1.7-0 | GUI UnboundLocalError fix |
| 1.7-1 | All crashes counted by coffee machine |
| 1.7-2 | Author statement (en/zh/ja), "Don't Open Issues" |
| 1.8-0 | Autonomous backend `xm`, lock files, .oil format, transaction state machine |
| 1.8-1 | Fix: autoremove timeout (15s→120s), D-Bus noise filter, silent exceptions |
| 1.9-0 | No-Apt Edition: zero apt-get/apt-cache, dual-format sources (deb + xpm) |
| 1.9-0+csharp | C# Special Edition: xmcs backend in C#, same architecture |

## Install

```bash
wget https://github.com/zizhao114514/xpm/releases/download/v1.9-0/xpm_1.9-0_all.deb
sudo dpkg -i xpm_1.9-0_all.deb
sudo apt-get install -f -y
xpm help
```

## Recommended BGM

- bunnycat — MY TOY
- bunnycat — Another Cup (reverse version)

## Author Statement

> 我感觉这玩意很稳定。如果有 bug，别去 issue，去找你的 AI。
> I feel this thing is quite stable. If you encounter any bugs, don't create an issue. Just ask your AI.
> これは安定していると思います。バグがある場合は、問題を起こすのではなく、自分の AI に聞いてください。

---
☕ *as if I care for your package manager.*
🛢️ Oil reserve: 100001% | Power: 1.x W | Systemd: explicitly not required

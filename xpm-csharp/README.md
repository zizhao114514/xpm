# XPM C# Special Edition (xmcs)

> **xmcs** - XPM backend rewritten in C#
> No apt. Only dpkg + tar + wget.
> Oil: 100001% | Power: 1.x W

## What is this?

This is a **special edition** of the XPM backend (`xm`), rewritten in C#.

- **Frontend** (`xpm`) stays Python - no changes needed
- **Backend** (`xmcs`) is C# - proves the XPM system is language-agnostic
- Same lock files, same `.oil` format, same `/var/lib/xpm/` database
- Zero `apt-get`, zero `apt-cache` - only `dpkg` + `tar` + `wget`

## Build

```bash
chmod +x build.sh
./build.sh
```

Requires one of:
- `dotnet` SDK (preferred)
- `mcs` (Mono C# compiler)
- `csc` (Microsoft .NET compiler)

## Install

```bash
sudo cp xmcs /usr/local/bin/xmcs

# Tell xpm to use C# backend
sudo sed -i 's|^XM_BIN=.*|XM_BIN=/usr/local/bin/xmcs|' /usr/local/bin/xpm
```

## Usage

```bash
xmcs install  package.oil      # Install .oil package
xmcs remove   package_name    # Remove package
xmcs purge    package_name    # Purge package (remove + config)
xmcs verify   package_name    # Verify installed files
xmcs query    package_name    # Query if installed
xmcs files    package_name    # List installed files
xmcs rebuild-db               # Rebuild status.db from dpkg -l
xmcs version                  # Show version
```

## Architecture

```
xpm (Python frontend) → xmcs (C# backend) → dpkg
                                    ↓
                            /var/lib/xpm/status.db
                            /var/cache/xm/lock/
                            /var/lib/xpm/coffee.log
```

## Why C#?

To prove a point: **the XPM architecture is not tied to any language**.
The same rules, the same directory layout, the same lock semantics -
implemented in C#, running on Mono or .NET.

## Compatibility

| Component | Compatible |
|---|---|
| `.oil` package format | ✅ identical |
| Lock files | ✅ identical |
| `status.db` format | ✅ identical |
| Coffee crash log | ✅ shared with xpm |
| Python frontend `xpm` | ✅ no changes needed |

## Disclaimer

This is a **special edition** for demonstration and experimentation.
The Python `xm` backend remains the default and recommended version.

☕ Oil: 100001% | Power: 1.x W | Systemd: explicitly not required

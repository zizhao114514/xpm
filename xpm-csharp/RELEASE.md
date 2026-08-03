# XPM C# Special Edition - Release Notes

## Version: 1.9-0-csharp

**Release Date:** 2026-08-03

### What's New

- Complete XPM backend (`xm`) rewritten in C#
- Zero `apt-get` / `apt-cache` calls (only `dpkg` + `tar` + `wget`)
- Full lock file support with `flock`-style advisory locking
- Transaction state machine (pending → running → committed → done)
- `.oil` package parsing (control, checksums, files.list)
- Shared coffee machine crash counter with Python frontend
- Compatible with Mono `mcs`, Microsoft `csc`, and `dotnet` SDK

### Files

| File | Description |
|---|---|
| `src/Program.cs` | Main entry point & command dispatch |
| `src/Xm.cs` | Core backend logic (install/remove/verify/query) |
| `src/LockFile.cs` | Advisory file locking |
| `src/OilPackage.cs` | .oil package parser |
| `src/Transaction.cs` | Transaction state machine |
| `src/Coffee.cs` | Shared crash counter |
| `src/DpkgWrapper.cs` | dpkg wrapper (only external PM call) |
| `build.sh` | Multi-compiler build script |
| `xmcs` | Compiled binary (Mono) |

### Compatibility

- Drop-in replacement for `xm` Python backend
- Same lock files, same database, same `.oil` format
- Frontend `xpm` requires zero changes

### Known Limitations

- `.oil` checksum verification is basic (full SHA256 validation pending)
- No GPG signature verification yet
- Tested on Debian 12 (bookworm) + Mono 6.x

---

☕ Oil: 100001% | Power: 1.x W | Systemd: no | Apt: forbidden

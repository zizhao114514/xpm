# XPM v2.0-3 — Debian-Native Edition

## 🐛 Bug Fixes (累计修复)

| 版本 | 问题 | 修复 |
|---|---|---|
| v2.0-1 | `control.tar.gz` gzip 流截断 | 改用 `gzip.GzipFile` 完整输出 |
| v2.0-2 | ar header 缺 1 字节 (`\n` vs `\x60\n`) | 严格 `struct.pack` 60 字节 |
| v2.0-2 | proot 下 `/opt/` 不可写 | 改到 `/usr/local/share/xpm/` |
| v2.0-2 | `md5sums` 缺失导致 apt 报错 | 自动生成 md5sums |
| **v2.0-3** | **dpkg 解包时目录不存在** | **postinst 提前 `mkdir -p` + 用 `dpkg-deb` 官方构建** |
| **v2.0-3** | **路径分裂（运行时 vs 包内）** | **全部统一到 `/usr/local/share/xpm/`** |
| **v2.0-3** | **sources.list.d 路径不一致** | **从 `/etc/xpm/` 改到 `/usr/local/share/xpm/sources.list.d/`** |

## ✅ 验证结果

```
dpkg-deb -I xpm_2.0-3_all.deb   → exit 0 ✅
dpkg-deb -c xpm_2.0-3_all.deb   → exit 0 ✅
gzip -t control.tar.gz           → OK ✅
gzip -t data.tar.gz              → OK ✅
ar t xpm_2.0-3_all.deb           → 3 members ✅
python3 tests/test_all.py        → 31/31 通过 ✅
```

## 📂 安装路径（全部统一）

| 文件类型 | 路径 |
|---|---|
| 前端 CLI + GUI | `/usr/local/bin/xpm` |
| 后端 | `/usr/local/bin/xm` |
| 构建工具 | `/usr/local/bin/xm-build` |
| .oil 打包工具 | `/usr/local/bin/xpm-build-tool` |
| 运行时数据库 | `/usr/local/share/xpm/db/` |
| 软件源配置 | `/usr/local/share/xpm/sources.list.d/` |
| 缓存 | `/usr/local/share/xpm/cache/` |
| 日志/历史 | `/usr/local/share/xpm/log/` |
| 文档 | `/usr/local/share/xpm/docs/` |
| 测试 | `/usr/local/share/xpm/tests/` |
| 桌面入口 | `/usr/share/applications/xpm.desktop` |

> **所有路径都在 `/usr/local/` 或 `/usr/share/` 下，proot / 真机 / 容器 100% 可写。**

## 📦 安装

```bash
wget https://github.com/zizhao114514/xpm/releases/download/v2.0-3/xpm_2.0-3_all.deb
sudo dpkg -i xpm_2.0-3_all.deb

xpm version
# xpm 2.0-3 "Debian-Native Edition"

xpm doctor
```

## 🔗 链接

- 仓库：https://github.com/zizhao114514/xpm
- Release：https://github.com/zizhao114514/xpm/releases/tag/v2.0-3

---

石油储备: 100001% | 功耗: 1.x W

> as if I care for your package dependencies.

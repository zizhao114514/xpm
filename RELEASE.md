# XPM v2.0-2 — Fixed Debian Package Edition

## 🐛 Bug Fix

| 问题 | 原因 | 修复 |
|---|---|---|
| `apt install ./xpm.deb` 报 "无效的归档签名" | `control.tar.gz` / `data.tar.gz` 的 gzip 流被截断（缺 CRC32 尾部） | 用 stdlib `gzip` + `tarfile` 重写构建器，确保字节级完整 |
| `dpkg-deb -c` 无法读取 | ar 成员 size 计算错误，对齐填充丢失 | 修正 ar header 格式（60 字节，右对齐零填充） |
| proot 下 `/opt/xpm/` 不可写 | proot 顶层目录权限受限 | 改到 `/usr/local/share/xpm/`（FHS 标准本地安装路径） |

## ✅ 验证结果

```
dpkg-deb -I xpm_2.0-2_all.deb   → exit 0 ✅
dpkg-deb -c xpm_2.0-2_all.deb   → exit 0 ✅
gzip -t control.tar.gz           → OK ✅
gzip -t data.tar.gz              → OK ✅
python3 tests/test_all.py        → 31/31 通过 ✅
```

## 📂 安装路径

| 文件类型 | 路径 |
|---|---|
| 前端 CLI + GUI | `/usr/local/bin/xpm` |
| 后端 | `/usr/local/bin/xm` |
| 文档 | `/usr/local/share/xpm/docs/` |
| 测试 | `/usr/local/share/xpm/tests/` |
| 桌面入口 | `/usr/share/applications/xpm.desktop` |

## 📦 安装

```bash
wget https://github.com/zizhao114514/xpm/releases/download/v2.0-2/xpm_2.0-2_all.deb
sudo dpkg -i xpm_2.0-2_all.deb
xpm doctor
```

## 🔗 链接

- 仓库：https://github.com/zizhao114514/xpm
- Release：https://github.com/zizhao114514/xpm/releases/tag/v2.0-2

---

石油储备: 100001% | 功耗: 1.x W

> as if I care for your package dependencies.

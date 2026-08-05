# XPM v2.0-6 — Filename-Fixed Edition

## 🐛 Bug Fixes (累计修复)

| 版本 | 问题 | 修复 |
|---|---|---|
| v2.0-1 | `control.tar.gz` gzip 流截断 | 改用 `gzip.GzipFile` 完整输出 |
| v2.0-2 | ar header 缺 1 字节 | 严格 `struct.pack` 60 字节 |
| v2.0-2 | proot 下 `/opt/` 不可写 | 改到 `/usr/local/share/xpm/` |
| v2.0-2 | `md5sums` 缺失导致 apt 报错 | 自动生成 md5sums |
| v2.0-3 | dpkg 解包时目录不存在 | postinst 提前 `mkdir -p` + `dpkg-deb` 官方构建 |
| v2.0-4 | `info()` 变量作用域覆盖 | 重命名为 `log_info/log_ok/log_warn/log_err` |
| v2.0-5 | `xpm mirrors` 拼出 `deb/dists/https://...` | `normalize_source()` 统一解析 |
| v2.0-5 | `build_package_index` 只取单 component | 遍历所有 component |
| **v2.0-6** | **`xpm install htop` 下载 404** | **用 Packages `Filename` 字段拼真实 `.deb` URL** |
| **v2.0-6** | **下载失败无诊断信息** | **打印真实 URL + HTTP 自动降级** |

## 🔥 v2.0-6 核心修复：`xpm install` 终于能下载了

### 根因
`download_package()` 从 Packages.gz URL 反推下载路径：
```python
# ❌ v2.0-5：从 Packages.gz 路径砍掉一段再拼
url = entry["_source"].rsplit("/",1)[0] + "/" + filename
# 结果：.../binary-amd64/pool/main/h/htop/htop_3.4.1-5_amd64.deb  ❌ 404
```

### 修复
Debian `Packages` 索引里每条记录都带 `Filename:` 字段，直接用它：
```python
# ✅ v2.0-6：base + Filename
ctrl["_base"] = s["base"]   # 源的 base URL
url = f"{entry['_base']}/{entry['Filename']}"
# 结果：https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/h/htop/htop_3.4.1-5_amd64.deb  ✅
```

### 验证（单元测试）
```
拼出 URL: https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/h/htop/htop_3.4.1-5_amd64.deb
期望 URL: https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/h/htop/htop_3.4.1-5_amd64.deb
匹配: True ✅

libtinfo6 URL: https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/n/ncurses/libtinfo6_6.5+20250216-2_amd64.deb ✅
```

## ✅ 验证结果

```
dpkg-deb -I xpm_2.0-6_all.deb   → exit 0 ✅
dpkg-deb -c xpm_2.0-6_all.deb   → exit 0 ✅ (22 个文件)
gzip -t control.tar.gz           → OK ✅
gzip -t data.tar.gz              → OK ✅
python3 tests/test_all.py        → 31/31 通过 ✅
```

## 📂 安装路径

| 文件类型 | 路径 |
|---|---|
| 前端 CLI | `/usr/local/bin/xpm` |
| 后端 | `/usr/local/bin/xm` |
| 构建工具 | `/usr/local/bin/xpm_build` |
| 运行时数据库 | `/usr/local/share/xpm/db/` |
| 软件源配置 | `/usr/local/share/xpm/sources.list.d/` |
| 缓存 | `/usr/local/share/xpm/cache/` |
| 日志/历史 | `/usr/local/share/xpm/log/` |
| 文档 | `/usr/local/share/xpm/docs/` |
| 测试 | `/usr/local/share/xpm/docs/tests/` |
| 桌面入口 | `/usr/share/applications/xpm.desktop` |

## 📦 安装

```bash
wget https://github.com/zizhao114514/xpm/releases/download/v2.0-6/xpm_2.0-6_all.deb
sudo dpkg -i xpm_2.0-6_all.deb

xpm version
# xpm 2.0-6 "Filename-Fixed Edition"

xpm update
xpm install htop        # ← 这次真的能下载了
xpm doctor
```

## 🔗 链接

- 仓库：https://github.com/zizhao114514/xpm
- Release：https://github.com/zizhao114514/xpm/releases/tag/v2.0-6

---

石油储备: 100001% | 功耗: 1.x W

> as if I care for your package dependencies.

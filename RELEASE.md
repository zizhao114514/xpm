# XPM v2.0-5 — Mirror-Fixed Edition

## 🐛 Bug Fixes (累计修复)

| 版本 | 问题 | 修复 |
|---|---|---|
| v2.0-1 | `control.tar.gz` gzip 流截断 | 改用 `gzip.GzipFile` 完整输出 |
| v2.0-2 | ar header 缺 1 字节 | 严格 `struct.pack` 60 字节 |
| v2.0-2 | proot 下 `/opt/` 不可写 | 改到 `/usr/local/share/xpm/` |
| v2.0-2 | `md5sums` 缺失导致 apt 报错 | 自动生成 md5sums |
| v2.0-3 | dpkg 解包时目录不存在 | postinst 提前 `mkdir -p` + `dpkg-deb` 官方构建 |
| v2.0-4 | `info()` 变量作用域覆盖 | 重命名为 `log_info/log_ok/log_warn/log_err` |
| **v2.0-5** | **`xpm mirrors` 拼出 `deb/dists/https://...`** | **新增 `normalize_source()` 统一解析，URL 拼接正确** |
| **v2.0-5** | **`build_package_index` 只取单 component** | **遍历所有 component，多源多段索引** |
| **v2.0-5** | **suite 带尾斜杠出现双斜杠** | **`strip("/")` 清理** |

## ✅ 验证结果

```
dpkg-deb -I xpm_2.0-5_all.deb   → exit 0 ✅
dpkg-deb -c xpm_2.0-5_all.deb   → exit 0 ✅ (22 个文件)
gzip -t control.tar.gz           → OK ✅
gzip -t data.tar.gz              → OK ✅
python3 tests/test_all.py        → 31/31 通过 ✅
```

## 🔧 `xpm mirrors` 修复详情

**v2.0-4 的错误输出：**
```
[i] 测试: deb/dists/https://mirrors.tuna.tsinghua.edu.cn/debian/Release
[!]   ❌ 超时/失败
```

**根因：** `test_mirrors()` 把 `parts[0]`（`"deb"`）拼进了 URL。

**v2.0-5 的正确输出：**
```
[i] 测试: https://mirrors.tuna.tsinghua.edu.cn/debian/dists/bookworm/Release
  ✅ Release: 312ms
  ✅ main: 428ms
  ✅ contrib: 401ms
  ✅ non-free: 395ms

🏆 tuna.list                    740ms   状态
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
| 测试 | `/usr/local/share/xpm/tests/` |
| 桌面入口 | `/usr/share/applications/xpm.desktop` |

## 📦 安装

```bash
wget https://github.com/zizhao114514/xpm/releases/download/v2.0-5/xpm_2.0-5_all.deb
sudo dpkg -i xpm_2.0-5_all.deb

xpm version
# xpm 2.0-5 "Mirror-Fixed Edition"

xpm update
xpm mirrors
xpm doctor
```

## 🔗 链接

- 仓库：https://github.com/zizhao114514/xpm
- Release：https://github.com/zizhao114514/xpm/releases/tag/v2.0-5

---

石油储备: 100001% | 功耗: 1.x W

> as if I care for your package dependencies.

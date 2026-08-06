# XPM 架构设计

## 1. 设计哲学

XPM 的设计遵循三条铁律：

1. **石油驱动（Oil-Driven）**：资源以石油储备百分比计量，而非传统的内存/磁盘
2. **禁止 apt**：`apt-get` / `apt-cache` 被明确禁止，仅使用 `wget` + `dpkg` + 自研后端
3. **后端语言无关**：前端是 Python，后端可以是 Python/C#/Rust/Go，只要遵守协议

## 2. 系统架构

```
┌─────────────────────────────────────────────┐
│              xpm (Python 前端)               │
│  ┌─────────┐ ┌─────────┐ ┌───────────────┐ │
│  │  CLI    │ │  GUI    │ │  Diagnostics  │ │
│  └────┬────┘ └────┬────┘ └───────┬───────┘ │
│       └─────────────┴──────────────┘        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Dependency│  │ Database │  │  Sources  │  │
│  │ Resolver  │  │  (JSON)  │  │  Parser  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
└───────┼───────────────┼─────────────┼────────┘
        │               │             │
        ▼               ▼             ▼
┌─────────────────────────────────────────────┐
│           xm / xmcs (后端)                 │
│  ┌────────┐  ┌────────┐  ┌───────────┐  │
│  │  Lock  │  │  GPG   │  │ Rollback  │  │
│  └───┬────┘  └───┬────┘  └─────┬─────┘  │
│      └──────────────┴─────────────┘        │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
        ┌──────────────────┐
        │  dpkg (解包引擎)  │
        └──────────────────┘
```

## 3. 数据流

### 3.1 安装流程

```
用户: xpm install vim
  │
  ▼
[1/4] 正在选中未安装的软件包：vim
  │
  ▼
DependencyResolver.resolve("vim")
  ├── 解析 Depends: vim-common (= 2:9.1), libtinfo6 (>= 6)
  ├── 递归解析每个依赖
  └── 返回有序列表: [libtinfo6, vim-common, vim]
  │
  ▼
[2/4] 正在选中 vim (2:9.1.0964-1)
  │
  ▼
对每个包:
  ├── wget 下载 .deb (进度条)
  ├── 校验 SHA256
  ├── Transaction.snapshot() 保存旧文件
  ├── [3/4] 正在解压 vim (2:9.1.0964-1)...
  │     └── xm install <file.deb> → dpkg -i
  └── [4/4] 正在设置 vim (2:9.1.0964-1)...
        └── 执行 postinst 脚本
  │
  ▼
PackageDB.add(name, version, files)
  │
  ▼
✅ 安装完成
```

### 3.2 卸载流程

```
用户: xpm remove vim
  │
  ▼
[1/3] 正在寻找与 vim 相关的文件...
  ├── PackageDB 查 files.list
  └── 检查是否有其他包依赖 vim
  │
  ▼
[2/3] 正在卸载 vim (2:9.1.0964-1)...
  └── xm remove vim → dpkg --remove vim
  │
  ▼
[3/3] 正在清除 vim (2:9.1.0964-1)...
  └── 删除 /etc/xpm/configs/vim/
  │
  ▼
PackageDB.remove("vim")
  │
  ▼
✅ 卸载完成
```

## 4. 源格式

### 4.1 Debian 格式
```
deb <url> <suite> [components...]
```
解析后转换为内部 Source 结构。

### 4.2 XPM 原生格式
```
[xpm]
name=Petroleum Stable
url=http://repo.example.com/dists/stable
type=xpm
enabled=yes
gpg_key=http://repo.example.com/keys/repo-key.gpg
```

### 4.3 统一内部表示
```python
Source = {
    "name":     str,
    "type":     "deb" | "xpm",
    "url":      str,
    "suite":   str,       # deb only
    "components": [str],   # deb only
    "arch":     str,
    "enabled":  bool,
    "gpg":      str | None,
}
```

## 5. 包格式 (.oil)

```
package.oil (tar.gz)
├── usr/bin/program
├── usr/share/man/man1/program.1
├── etc/program.conf
└── xpm/
    ├── control          # Package/Version/Depends/Architecture
    ├── files.list       # 文件清单
    ├── checksums.sha256 # SHA256 校验
    └── pmadd/          # 包管理脚本
        ├── preinst
        ├── postinst
        ├── prerm
        └── postrm
```

## 6. 数据库设计

### 6.1 status.db (JSON)
```json
{
  "vim": {
    "version": "2:9.1.0964-1",
    "installed_at": "2026-08-04T15:30:00",
    "files": ["usr/bin/vim", "usr/share/man/man1/vim.1.gz"],
    "source": "tuna-bookworm",
    "architecture": "arm64"
  }
}
```

### 6.2 coffee.json
```json
{"crashes": 42}
```

### 6.3 回滚快照
```json
{
  "pkg": "vim",
  "timestamp": "2026-08-04T15:30:00",
  "files": {
    "/usr/bin/vim": "<base64>",
    "/etc/vim/vimrc": "<base64>"
  }
}
```

## 7. 后端协议

后端（xm/xmcs）通过 stdin/stdout 与前端通信：

### 7.1 安装
```
前端 → 后端: install <file_path>
后端 → 前端: OK\n 或 ERROR: <msg>\n
```

### 7.2 卸载
```
前端 → 后端: remove <package_name>
后端 → 前端: OK\n 或 ERROR: <msg>\n
```

### 7.3 校验
```
前端 → 后端: verify <package_name>
后端 → 前端: OK\n 或 FAIL: <reason>\n
```

## 8. 安全模型

| 层 | 机制 |
|---|---|
| 下载 | HTTPS + SHA256 校验 |
| 签名 | GPG Release 签名 |
| 安装 | dpkg 权限检查 |
| 锁 | flock 防止并发 |
| 回滚 | 文件快照 + 事务日志 |

## 9. 性能考虑

- 索引缓存：`/var/cache/xpm/*-Packages` 本地缓存
- 数据库：JSON（小系统够用，万级包需换 SQLite）
- 下载：wget 流式 + 进度回调
- 依赖解析：纯内存图遍历，O(V+E)

## 10. 未来扩展

- [ ] Rust 后端 (xmrs)
- [ ] 增量更新（bsdiff）
- [ ] P2P 分发
- [ ] 原子事务（copy-on-write）
- [ ] 与 systemd/runit 服务管理集成

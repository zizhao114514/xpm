# XPM 内部实现

## 1. 核心模块

### 1.1 xpm.py (前端)
- 命令行解析
- 多语言支持 (en/zh/ja)
- 依赖解析器
- 事务管理
- GPG 校验
- GUI 启动

### 1.2 xm.py (Python 后端)
- dpkg 封装
- 文件锁 (flock)
- .oil 包解析
- 事务状态机

### 1.3 xmcs (C# 后端)
- 与 xm.py 功能等价
- 可互换
- 证明后端语言无关

## 2. 关键算法

### 2.1 依赖解析
```python
def resolve(pkg_name, all_pkgs, installed):
    # 1. 找包的所有版本，选最高
    candidates = [p for p in all_pkgs if p["package"] == pkg_name]
    pkg = max(candidates, key=version_key)
    
    # 2. 解析 Depends 字段
    deps = parse_depends(pkg.get("depends", ""))
    
    # 3. 对每个依赖（OR 组），选第一个满足的
    result = []
    for alt_group in deps:
        for name, op, ver in alt_group:
            if name in installed:
                break
            sub = resolve(name, all_pkgs, installed)
            result.extend(sub)
    
    # 4. 添加自己
    result.append((pkg_name, version, "selected"))
    return result
```

### 2.2 版本比较
```python
def compare_versions(v1, op, v2):
    # 1. 提取 epoch
    e1 = int(v1.split(":")[0]) if ":" in v1 else 0
    e2 = int(v2.split(":")[0]) if ":" in v2 else 0
    if e1 != e2:
        return e1 > e2 if op in (">=", ">") else e1 < e2
    
    # 2. 比较 upstream version（简化）
    # 实际实现用 distutils.version.LooseVersion
    from distutils.version import LooseVersion
    a, b = LooseVersion(v1), LooseVersion(v2)
    if op == ">=": return a >= b
    if op == ">":  return a > b
    if op == "<=": return a <= b
    if op == "<":  return a < b
    if op == "=":  return a == b
```

### 2.3 源解析状态机
```
文件 → 逐行读取
  ├── 以 "deb" 开头 → Debian 格式
  ├── 以 "[" 开头  → XPM 格式块
  └── 以 "#" 开头  → 注释，跳过

Debian: url + suite + components → Source
XPM:    [xpm] 块 → Source
```

## 3. 数据库 schema

### 3.1 status.db
```json
{
  "<package_name>": {
    "version": "<version>",
    "installed_at": "<ISO8601>",
    "files": ["<file_path>", ...],
    "source": "<source_name>",
    "architecture": "<arch>"
  }
}
```

### 3.2 coffee.json
```json
{"crashes": 42}
```

## 4. 网络层

### 4.1 wget 调用
```python
# 清除代理（防止 X11 会话泄漏）
env = os.environ.copy()
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
    env.pop(k, None)

# 进度条模式
cmd = ["wget", "--progress=bar:force:noscroll",
        "--timeout=60", "-O", dest, url]
proc = subprocess.Popen(cmd, stderr=PIPE, text=True)
for line in proc.stderr:
    if "%" in line:
        # 解析百分比、速度、ETA
        update_progress(line)
```

### 4.2 源索引路径
```
Debian: {url}/dists/{suite}/{comp}/binary-{arch}/Packages.gz
XPM:    {url}/Packages.gz
```

## 5. GUI 架构

```
┌─────────────────────────────┐
│  Top Bar (搜索/安装/卸载/升级) │
├─────────────────────────────┤
│  Progress Panel              │
│  ├── Label: 当前操作         │
│  └── Bar: 进度条            │
├─────────────────────────────┤
│  Package List (TreeView)     │
│  ├── 包名 │ 版本 │ 状态     │
├─────────────────────────────┤
│  Log Window (ScrolledText)   │
│  └── 实时日志               │
└─────────────────────────────┘
```

### 线程模型
```
Main Thread (Tkinter)
  ├── Button Click
  └── spawn Worker Thread
        ├── wget download
        ├── xm install
        └── queue → Main Thread (UI update)
```

## 6. 后端协议

### 6.1 进程间通信
```
前端 → 后端: subprocess.run([xm_bin, action, arg])
后端 → 前端: stdout (结果) + stderr (错误)
退出码: 0=成功, 非0=失败
```

### 6.2 锁机制
```
/var/lock/xpm/lock  (flock)
├── 安装时获取
├── 卸载时获取
└── 超时 30s 后放弃
```

## 7. 构建系统

### 7.1 .deb 构建
```
build_deb.py
├── 构建 control.tar.gz (control + postinst + prerm)
├── 构建 data.tar.gz (xpm.py + xm.py + docs + tests)
├── 写 debian-binary
└── ar 归档 → xpm_2.0-0_all.deb
```

### 7.2 .oil 构建
```
xpm build <dir>
├── 读 xpm/control
├── 遍历目录 → files.list
├── SHA256 每个文件 → checksums.sha256
└── tar czf → <name>_<ver>_<arch>.oil
```

## 8. 测试策略

### 8.1 单元测试
- 版本比较
- 依赖解析
- 源解析
- 数据库 CRUD
- 回滚/恢复

### 8.2 集成测试
- 完整安装流程（模拟）
- 依赖链解析
- 循环依赖处理

### 8.3 运行
```bash
python3 tests/test_all.py
# 36 passed in 0.8s
```

## 9. 性能分析

| 操作 | 时间复杂度 | 实际耗时（1000包） |
|---|---|---|
| 依赖解析 | O(V + E) | < 50ms |
| 源更新 | O(sources × comps) | 5-30s（网络） |
| 包搜索 | O(N) | < 10ms |
| 安装 | O(deps) × wget | 网络瓶颈 |
| 数据库查询 | O(1) | < 1ms |

## 10. 已知限制

1. **数据库用 JSON** → 万级包需换 SQLite
2. **无增量更新** → 每次全量下载 Packages.gz
3. **无并行下载** → 一次一个包
4. **GPG 可选** → 不强制签名验证
5. **无 delta 更新** → 大包全量下载

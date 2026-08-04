# XPM 用户手册

## 1. 入门

### 1.1 安装 XPM
```bash
wget https://github.com/zizhao114514/xpm/releases/download/v2.0-0/xpm_2.0-0_all.deb
sudo dpkg -i xpm_2.0-0_all.deb
# 如果提示缺少依赖：
sudo apt-get install -f -y   # 这是最后一次用 apt
```

### 1.2 首次配置
```bash
sudo -i
xpm doctor          # 诊断系统
xpm sources         # 查看源
xpm update          # 更新索引
```

## 2. 日常使用

### 2.1 搜索
```bash
xpm search vim
# 输出:
# 🔍 搜索结果 'vim':
#   vim                          2:9.1.0964-1  [editors]
#   vim-common                   2:9.1.0964-1  [editors]
```

### 2.2 安装
```bash
xpm install vim
# 输出:
# [1/4] 正在选中未安装的软件包：vim
# [2/4] 正在选中 vim (2:9.1.0964-1)
# [2/4] 正在选中 libtinfo6 (6.4+20230625-2)
# [3/4] 正在解压 vim (2:9.1.0964-1)...
# [3/4] 正在解压 libtinfo6 (6.4+20230625-2)...
# [4/4] 正在设置 vim (2:9.1.0964-1)...
# ✅ 安装完成
```

### 2.3 卸载
```bash
xpm remove vim
# 输出:
# [1/3] 正在寻找与 vim 相关的文件...
# [2/3] 正在卸载 vim (2:9.1.0964-1)...
# [3/3] 正在清除 vim (2:9.1.0964-1)...
# ✅ 已彻底清除
```

### 2.4 升级
```bash
xpm upgrade
# 自动比对版本，逐个升级
```

### 2.5 查看信息
```bash
xpm info vim
xpm depends vim
xpm rdepends vim
```

## 3. 高级功能

### 3.1 回滚
```bash
xpm rollback list          # 查看回滚点
xpm rollback 1234567890   # 回滚到指定点
```

### 3.2 构建包
```bash
xpm build myprogram/
# 目录结构:
# myprogram/
# ├── usr/bin/myprog
# └── xpm/control
```

### 3.3 校验
```bash
xpm verify              # 校验所有已安装包
xpm verify vim          # 校验指定包
```

### 3.4 修复
```bash
xpm fix-broken          # 修复中断的安装
```

## 4. GUI 使用

```bash
xpm gui
```

GUI 功能：
- 搜索框 + 安装/卸载按钮
- 实时进度条
- 进行中操作面板
- 日志窗口（实时滚动）
- 包列表（含安装状态）

## 5. 源管理

### 5.1 添加 Debian 源
```bash
sudo nano /etc/xpm/sources.list.d/tuna.list
# 内容:
# deb http://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free
```

### 5.2 添加 XPM 源
```bash
sudo nano /etc/xpm/sources.list.d/petroleum.list
# 内容:
# [xpm]
# name=Petroleum Stable
# url=http://repo.example.com/dists/stable
# type=xpm
# enabled=yes
```

### 5.3 更新索引
```bash
xpm update
```

## 6. 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `XM_BIN` | `/usr/local/bin/xm` | Python 后端路径 |
| `XMCS_BIN` | `/usr/local/bin/xmcs` | C# 后端路径 |
| `XPM_ROOT` | `/var/lib/xpm` | 数据库目录 |
| `XPM_CACHE` | `/var/cache/xpm` | 缓存目录 |
| `LANG` | (系统默认) | 语言选择 |

## 7. 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 一般错误 |
| 130 | 用户中断 (Ctrl+C) |

## 8. 文件位置

| 路径 | 用途 |
|---|---|
| `/etc/xpm/sources.list.d/` | 源配置 |
| `/var/lib/xpm/status.db` | 已安装包数据库 |
| `/var/lib/xpm/coffee.json` | 崩溃计数 |
| `/var/lib/xpm/rollback/` | 回滚快照 |
| `/var/cache/xpm/archives/` | 下载缓存 |
| `/var/cache/xpm/*-Packages` | 源索引 |
| `/var/log/xpm/` | 日志 |

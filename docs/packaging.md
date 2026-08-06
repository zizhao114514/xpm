# XPM 打包指南

## 1. 目录结构

```
myprogram/
├── usr/
│   ├── bin/
│   │   └── myprog          ← 可执行文件
│   └── share/
│       ├── man/
│       │   └── man1/
│       │       └── myprog.1  ← man 手册
│       └── doc/
│           └── myprog/
│               └── README
├── etc/
│   └── myprog.conf          ← 配置文件
└── xpm/
    ├── control              ← 包元数据（必需）
    ├── files.list           ← 文件清单（构建时自动生成）
    ├── checksums.sha256    ← 校验和（构建时自动生成）
    └── pmadd/              ← 包管理脚本（可选）
        ├── preinst          ← 安装前执行
        ├── postinst         ← 安装后执行
        ├── prerm            ← 卸载前执行
        └── postrm           ← 卸载后执行
```

## 2. control 文件

```
Package: myprog
Version: 1.0-1
Architecture: all
Depends: libc6 (>= 2.28), libssl3
Section: utils
Priority: optional
Description: 我的程序
 这是程序的长描述。
 可以多行，每行缩进一个空格。
```

### 字段说明

| 字段 | 必需 | 说明 |
|---|---|---|
| Package | ✅ | 包名（小写，无空格） |
| Version | ✅ | 版本号（可含 epoch: 如 `2:1.0`） |
| Architecture | ✅ | `all` / `amd64` / `arm64` / `i386` |
| Depends | ❌ | 依赖列表 |
| Section | ❌ | 分类 |
| Priority | ❌ | 优先级 |
| Description | ✅ | 描述（首行短描述，后续长描述） |

### Depends 语法

```
Depends: libc6 (>= 2.28), libssl3
# 多依赖用逗号分隔

Depends: libgtk-3-0 | libgtk-4-0, libc6
# | 表示 OR 选择

Depends: python3:any (>= 3.8)
# :any 表示任意架构
```

## 3. 构建

```bash
xpm build myprogram/
# 输出: myprog_1.0-1_all.oil
```

构建过程：
1. 读取 `xpm/control`
2. 遍历目录，生成 `xpm/files.list`
3. 计算每个文件 SHA256，写入 `xpm/checksums.sha256`
4. 打包为 `.oil`（tar.gz）

## 4. 包管理脚本

### preinst（安装前）
```bash
#!/bin/sh
set -e
# 检查系统要求
if ! command -v python3 >/dev/null; then
    echo "需要 python3"
    exit 1
fi
# 备份旧配置
[ -f /etc/myprog.conf ] && cp /etc/myprog.conf /etc/myprog.conf.bak
exit 0
```

### postinst（安装后）
```bash
#!/bin/sh
set -e
# 创建用户
useradd -r -s /sbin/nologin myprog 2>/dev/null || true
# 设置权限
chmod 755 /usr/bin/myprog
chown root:root /usr/bin/myprog
# 更新缓存
echo "myprog installed successfully"
exit 0
```

### prerm（卸载前）
```bash
#!/bin/sh
set -e
# 停止服务
systemctl stop myprog 2>/dev/null || true
exit 0
```

### postrm（卸载后）
```bash
#!/bin/sh
set -e
# 清理
rm -f /etc/myprog.conf.bak
# 删除用户
userdel myprog 2>/dev/null || true
exit 0
```

## 5. 安装自研包

```bash
# 方式 1: 直接指定文件
xpm install ./myprog_1.0-1_all.oil

# 方式 2: 放到源目录后 update
cp myprog_1.0-1_all.oil /var/cache/xpm/archives/
xpm update
xpm install myprog
```

## 6. 签名

### 生成密钥
```bash
gpg --gen-key
gpg --export --armor your-key-id > public.key
```

### 签名包
```bash
gpg --local-user your-key-id --detach-sign myprog_1.0-1_all.oil
# 生成 myprog_1.0-1_all.oil.sig
```

### 在源中配置
```
[xpm]
name=My Repo
url=http://repo.example.com/dists/stable
type=xpm
gpg_key=http://repo.example.com/keys/public.key
enabled=yes
```

## 7. 最佳实践

1. **一个包一个功能**：不要打包"全家桶"
2. **显式声明依赖**：不要假设系统有某个库
3. **配置文件放 /etc**：运行时数据放 /var
4. **脚本保持简单**：preinst/postinst 要快速执行
5. **版本号递增**：遵循 Debian 版本规范
6. **测试安装/卸载**：在干净环境中验证
7. **写 man 手册**：`/usr/share/man/man1/`
8. **签名你的包**：GPG 签名是信任的基础

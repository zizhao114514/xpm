# XPM v2.0-0 "Complete Edition" Release Notes

## 🎯 版本定位

XPM 第一个**完整可用**的版本。从 v2.0-0 起，XPM 不再是一个"有趣的玩具"，而是一个**真正能替代 apt 的包管理器**。

## ✨ 新增功能

### 1. 依赖解析器
- 解析 `Depends:` 字段
- 支持 OR 关系（`|`）
- 支持版本约束（`>=`, `>`, `=`, `<`, `<=`）
- Debian epoch 版本比较
- 拓扑排序安装顺序
- 循环依赖检测

### 2. 事务回滚
- 安装前自动快照文件
- `xpm rollback list` 查看回滚点
- `xpm rollback <id>` 一键回滚

### 3. GPG 签名校验
- Release 文件签名验证
- 包级别签名支持
- 密钥环管理

### 4. 包构建工具
- `xpm build <dir>` 将目录打包为 `.oil`
- 自动生成 `files.list` 和 `checksums.sha256`
- 支持 GPG 签名

### 5. 完整测试套件
- 36 个测试全部通过
- 覆盖版本比较、依赖解析、回滚、构建、GPG、源解析

### 6. 完整文档
- `docs/design.md` — 架构设计
- `docs/manual.md` — 用户手册
- `docs/packaging.md` — 打包指南
- `docs/FAQ.md` — 常见问题
- `docs/internals.md` — 内部实现

## 🖥️ CLI 输出规范

### 安装（4 阶段）
```
[1/4] 正在选中未安装的软件包：vim
[2/4] 正在选中 vim (2:9.1.0964-1)
[2/4] 正在选中 libtinfo6 (6.4+20230625-2)
[3/4] 正在解压 vim (2:9.1.0964-1)...
[3/4] 正在解压 libtinfo6 (6.4+20230625-2)...
[4/4] 正在设置 vim (2:9.1.0964-1)...
[4/4] 正在设置 libtinfo6 (6.4+20230625-2)...
✅ 安装完成
```

### 卸载（3 阶段）
```
[1/3] 正在寻找与 vim 相关的文件...
[2/3] 正在卸载 vim (2:9.1.0964-1)...
[3/3] 正在清除 vim (2:9.1.0964-1)...
✅ 已彻底清除
```

### 下载进度
```
📥 下载 vim_9.1.0964-1_arm64.deb (3.2MB)
  ████████████████░░░░ 78% | 1.4MB/s | ETA 9s
```

## 🔧 新增命令

| 命令 | 说明 |
|---|---|
| `xpm reinstall <pkg>` | 重新安装 |
| `xpm fix-broken` | 修复中断的安装 |
| `xpm depends <pkg>` | 显示依赖 |
| `xpm rdepends <pkg>` | 显示反向依赖 |
| `xpm rollback list` | 列出回滚点 |
| `xpm rollback <n>` | 回滚到指定点 |
| `xpm build <dir>` | 构建 .oil 包 |
| `xpm verify [pkg]` | 校验完整性 |
| `xpm doctor` | 系统诊断 |
| `xpm stats` | 统计信息 |

## 🚫 铁律

- **零 apt-get / apt-cache 调用**
- **仅 wget + dpkg + xm/xmcs**
- **代理环境变量自动清除**
- **所有输出 flush，防止 proot/X11 缓冲**

## 📊 测试

```
tests/test_all.py: 36 passed in 0.8s
```

## 🔗 下载

```
.deb: https://github.com/zizhao114514/xpm/releases/download/v2.0-0/xpm_2.0-0_all.deb
源码: https://github.com/zizhao114514/xpm/archive/refs/heads/main.zip
```

## ☕ 咖啡机

```
Total crashes: 300000000042
Oil reserve: 100001%
Power: 1.x W
```

🛢️ Oil-driven. Apt-forbidden. Language-agnostic.

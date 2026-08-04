# XPM 常见问题 (FAQ)

## Q1: 为什么 XPM 不使用 apt？

**A:** 设计哲学决定。apt 是一个庞大的体系，依赖 systemd、复杂的依赖解析器、网络管理等。XPM 的设计目标是：
- 最小依赖（仅 wget + dpkg）
- 后端语言无关
- 可嵌入自制系统
- 石油驱动 😄

## Q2: XPM 和 apt 能共存吗？

**A:** 可以，但不推荐。XPM 不卸载 apt，只是**禁用**它。在 PetroOS 中，apt 被移除。在 Debian 中，你可以同时用两者，但**不要混用**（用 XPM 装的包不要再用 apt 操作）。

## Q3: `.oil` 格式是什么？

**A:** `.oil` 本质上是 **tar.gz** 文件，包含：
- 程序文件
- `xpm/control` 元数据
- `xpm/files.list` 文件清单
- `xpm/checksums.sha256` 校验和
- 可选的 `xpm/pmadd/` 脚本

## Q4: 为什么 GUI 在 proot + X11 下卡住？

**A:** 三个常见原因：
1. **软键盘回车不生效** → 用 Hacker's Keyboard
2. **sudo 没 tty** → 用 `sudo -i` 启动 GUI
3. **代理环境变量污染** → XPM 会自动清除，但手动检查 `env | grep proxy`

## Q5: 如何回滚一次失败的升级？

```bash
xpm rollback list          # 查看回滚点
xpm rollback 1234567890   # 回滚到指定点
```

每次安装前 XPM 会自动创建快照。

## Q6: 可以在没有 root 的情况下使用 XPM 吗？

**A:** 部分可以。搜索、查看信息不需要 root。安装/卸载/升级需要 root（因为要写 `/usr/`、`/etc/` 等系统目录）。

## Q7: XPM 支持哪些架构？

**A:** 任何 dpkg 支持的架构都支持：
- amd64 (x86_64)
- arm64 (aarch64)
- armhf
- i386
- riscv64
- 等等

## Q8: 如何创建自己的软件源？

```bash
# 1. 创建目录结构
mkdir -p myrepo/dists/stable/main/binary-amd64

# 2. 把所有 .oil 包放进去
cp *.oil myrepo/dists/stable/main/binary-amd64/

# 3. 生成 Packages 文件
cd myrepo/dists/stable/main/binary-amd64/
dpkg-scanpackages . > Packages
gzip -k Packages

# 4. 配置 XPM 源
echo "[xpm]" > /etc/xpm/sources.list.d/myrepo.list
echo "name=MyRepo" >> /etc/xpm/sources.list.d/myrepo.list
echo "url=http://my-server/myrepo/dists/stable" >> /etc/xpm/sources.list.d/myrepo.list
echo "type=xpm" >> /etc/xpm/sources.list.d/myrepo.list
echo "enabled=yes" >> /etc/xpm/sources.list.d/myrepo.list
```

## Q9: 咖啡机崩溃计数有什么用？

**A:** 它是一个幽默化的**系统健康指标**。每次异常（下载失败、超时、依赖缺失等）都会计数。高崩溃数意味着系统不稳定，需要检查。

## Q10: 如何卸载 XPM 本身？

```bash
sudo dpkg --purge xpm
# 或
sudo xpm remove xpm  # 自举卸载（不建议）
```

## Q11: XPM 能在 macOS 上运行吗？

**A:** 不能。XPM 依赖 dpkg 和 Linux 目录结构。macOS 用户请使用 Homebrew。

## Q12: 什么是"石油储备 100001%"？

**A:** 这是 XPM 的招牌彩蛋。它意味着资源充裕到溢出，一切都不是问题。类比："我们的储备多到可以泄漏。"

## Q13: 我可以在生产环境使用 XPM 吗？

**A:** v2.0-0 是第一个"完整版"，适合：
- ✅ 个人开发机
- ✅ 测试环境
- ✅ 自制系统
- ⚠️ 生产服务器（建议先在测试环境验证）
- ❌ 关键基础设施（等 v3.0 稳定版）

## Q14: 如何贡献代码？

```bash
git clone https://github.com/zizhao114514/xpm.git
cd xpm
# 修改代码
python3 tests/test_all.py  # 确保测试通过
# 提交 PR
```

## Q15: "as if I care" 是什么意思？

**A:** 这是 XPM 的态度宣言。意思是：
> "我才不在乎你的包依赖有多复杂，我的石油储备够用就行。"

这是半开玩笑的傲慢，体现了 XPM 的设计自信——它不试图讨好所有人，它只做对的事。

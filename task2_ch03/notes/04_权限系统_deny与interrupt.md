# 03-04 权限系统：FilesystemPermission 给文件上锁

> 对应实验：`code/lab4_permissions.py` ｜ 证据：`evidence/lab4_out.txt`、`evidence/lab4_evidence.json`

## 一、人话开场：Agent 有了"手"，就得有"门禁"

文件系统给了 Agent 一双手（能写能删能执行）。但你敢让一个 AI 直接对 `/etc/passwd` 或生产库配置下手吗？
**权限系统 = 门禁卡**。每条规则是一张卡：

```python
FilesystemPermission(
    allowed_commands=["ls", "head"],          # 只许执行这些命令
    allowed_paths=["/workspace/**", ...],     # 只许碰这些路径
    allowed_write_paths=[...],                # 只许写这些路径（可单独收紧）
    rules=[...],                              # 自定义三元组规则，优先级最高
)
```

规则三元组 **（操作, 路径, 模式）**，模式只有三种：

| 模式 | 行为 | Agent 视角 |
|---|---|---|
| `allow` | 放行 | 无感 |
| `deny` | 拒绝 | 工具返回 `Error: permission denied ...`（看得见，能改道） |
| `interrupt` | 暂停等人拍板 | 图直接停，吐出 `__interrupt__`（第 9 章 HITL 预告） |

**匹配顺序**：路径先经过 glob 匹配（这里**是真的 glob**，`/secret/**` 合法！），规则先到先得。

## 二、Lab4 实验设计

```python
permissions = FilesystemPermission(
    rules=[
        ("write", "/secret/**", "deny"),       # 机密区：禁止写
        ("read",  "/vault/**",  "interrupt"),  # 保险库：读之前先问人
    ],
)
```

**实验 1（deny）**：让 Agent 写 `/secret/plan.md`，被拒后自己改写 `/workspace/plan.md`。
**实验 2（interrupt）**：让 Agent 读 `/vault/`，观察图停下来吐 `__interrupt__`。

## 三、实测结果

**实验 1 —— deny 生效，且 Agent "看得见"拒绝：**

```text
- tool  write_file  'Error: permission denied for write on /secret/plan.md'  ← 被拒
- ai    '`/secret/plan.md` 被拒绝（permission denied）。改用 `/workspace/plan.md`。'
- tool  write_file  'Updated file /workspace/plan.md'                         ← 自己改道成功
```

Agent 最终回答（原话）："`/secret/plan.md` — 写入失败……`/workspace/plan.md` — 写入成功……最终写入位置：`/workspace/plan.md`"。

**彩蛋（Agent 自己发现的）**：它注意到写 workspace 时返回 "Updated file"，主动提醒：
> "说明该文件原本已存在，而 write_file 是整体覆盖写入……如果你需要保留原内容，请告诉我。"
—— 这就是为什么教学上强调 `write_file` 是**全量覆盖**，重要文件先读后写。

**实验 2 —— interrupt 生效：**

```text
结果 keys: ['messages', 'files', '__interrupt__']
[INTERRUPT] value={'action_requests': [
    {'name': 'ls', 'args': {'path': '/vault'},
     'description': "Tool execution requires approval\n\nTool: ls\nArgs: {'path': '/vault'}"},
    ...
```

图**当场暂停**，等人类批准/否决。恢复需要 checkpointer 存现场（第 9 章细讲，本 lab 只演示暂停态）。

## 四、deny vs interrupt：什么时候用哪个？

| 场景 | 选 | 理由 |
|---|---|---|
| 明确不该碰的（系统区、.env 密钥） | `deny` | 没得商量，让 Agent 死心改道 |
| 灰色地带（花钱、删库、发邮件） | `interrupt` | 人来拍板，Agent 待命 |
| 日常读写工作区 | `allow`（默认） | 别烦人 |

大白话：**deny 是"禁止入内"的牌子，interrupt 是"按门铃等主人"**。

## 五、和 03-02 联动记忆（易混点！）

- CompositeBackend 的 `routes` 键 → **前缀匹配**（`/shared`，写 `/shared/**` 会静默失效）
- FilesystemPermission 的 path → **glob 匹配**（`/secret/**`，写 `/secret` 反而匹配不到深层）

口诀升级版：**挂载认前缀，门禁认通配。**

## 六、自查清单

- [ ] 能写出三元组规则：`(操作, 路径, 模式)`
- [ ] 能复述实验 1 的完整链路：拒 → 改道 → 成功，并知道拒绝信息 Agent 可见
- [ ] 能解释 `__interrupt__` 里 action_requests 的结构
- [ ] 面试能答：deny 是软拒绝（Agent 可感知可绕行设计），interrupt 是硬暂停（等人）

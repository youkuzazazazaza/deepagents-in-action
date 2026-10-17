# 03-01 虚拟文件系统：Agent 的"草稿本"（StateBackend 实战）

> 对应实验：`code/lab1_state_backend.py` ｜ 证据：`evidence/lab1_out.txt`、`evidence/lab1_r1_files.json`

## 一、先说人话：为什么 Agent 需要一个"假电脑"？

想象你雇了个聪明但**记性只有 5 分钟**的实习生（大模型的上下文窗口就是他的工作记忆）。

你让他"分析这份 500 页的报告，写个摘要"。他会怎么办？

- **没有文件系统的 Agent**：只能把 500 页全塞进"脑子"（上下文）→ 爆窗，或者读一段忘一段，前后矛盾。
- **有文件系统的 Agent**：先在桌上摊开一张草稿纸（虚拟文件），"第 1-50 页讲财务，先记下来"——写到 `/notes/财务.md`；读到后面发现新线索，翻回草稿纸改两笔。**草稿纸就是他的外部记忆**。

这就是 DeepAgents 的核心 trick：**把"思考的过程"外置成文件操作**。
官方叫法是 **Back-of-the-Notebook**（笔记本背面），《Deep Agents》论文里 Anticipation 就是指：Agent 会主动"未雨绸缪"地建目录、写计划、留笔记，而不是一口气硬算。

大白话三件套：

| 概念 | 大白话 | 类比你电脑上的 |
|---|---|---|
| 虚拟文件系统 | Agent 的草稿本+工作台 | C 盘 / 桌面 |
| `files` 状态 | 草稿本当前每一页的内容 | 内存里的文件夹快照 |
| StateBackend | 把草稿本放在**内存**里，进程关了就没 | RAM 盘 |

## 二、Lab1 实验设计（三幕剧）

**问题**：StateBackend 说是"内存盘"，那"内存"意味着什么？怎么证明它易失？怎么证明文件能"续命"？

三幕剧设计：

1. **第 1 幕（写→读→列）**：让 Agent 往 `/workspace/todo.md` 写待办清单，读回来，再 `ls`。验证工具三件套真的在工作。
2. **第 2 幕（撕掉草稿本）**：开一个**全新的** `invoke`，不带任何 `files`，让 Agent `ls /workspace`。如果虚拟文件系统是内存态，这里应该**空空如也**。
3. **第 3 幕（草稿本复活）**：把第 1 幕结束时拿到的 `files` 快照塞回去，再让 Agent 读 `/workspace/todo.md`。文件应该"复活"。

## 三、关键命令与代码

```bash
cd /root/ch03_labs
/root/research_deepagent/.venv/bin/python \
  /mnt/d/gitcode/learn/deepagents-in-action/task2_ch03/code/lab1_state_backend.py
```

核心代码只有三行概念：

```python
backend = StateBackend()          # 内存盘
agent = create_deep_agent(
    model=model,
    instructions="...",
    backend=backend,
)
r1 = agent.invoke({"messages": [...]})   # 第 1 幕
snapshot = r1["files"]                   # ★ 把草稿本拍下来
# 第 3 幕：invoke 时带上 files=快照 → 复活
```

**预期输出**（实测证据 `lab1_out.txt`）：

```text
==== 第1轮：写→读→列 ====
- tool  write_file  'Updated file /workspace/todo.md'
- tool  read_file   '1  - [ ] 买牛奶 2  - [ ] 写周报'
- tool  ls          "['/workspace/todo.md']"
---- files（虚拟磁盘快照）----
[file] /workspace/todo.md  (19 chars)

==== 第2轮：全新 invoke（没带 files）→ 草稿本被撕了 ====
- tool  ls  'No files found'          ← 空了！

==== 第3轮：带上 files 接力 → 文件复活 ====
- tool  read_file  '1  - [ ] 买牛奶 2  - [ ] 写周报'   ← 复活了！
```

## 四、`files` 快照里到底长什么样？（源码级）

`lab1_r1_files.json` 完整内容：

```json
{
 "/workspace/todo.md": {
  "content": "- [ ] 买牛奶\n- [ ] 写周报",
  "encoding": "utf-8",
  "created_at": "2026-10-15T14:49:12.273804+00:00",
  "modified_at": "2026-10-15T14:49:12.273804+00:00"
 }
}
```

**为什么重要**：这不是随随便便的字典——

1. `content` 是字符串本体（还带 `\n` 转义）；
2. `created_at` / `modified_at` 时间戳，是**变更检测**的依据（第 6 章 human-in-the-loop 会靠它判断"文件被改过没"）；
3. ⚠️ **踩坑实录**：如果你自己预置文件，值**必须**是 `{"content": "..."}` 这种字典！直接写 `"/a.md": "内容字符串"` 会在 read_file 时炸出 `TypeError: string indices must be integers, not 'str'`（`_normalize_content` 会去做 `file_data["content"]`，拿到字符串就当索引用了）。这是本人在 lab3 里亲手踩的坑。

## 五、大白话复盘：三个 "为什么"

**Q1：为什么 `ls` 会 "No files found"？明明上一轮刚写的！**
因为 StateBackend 的"磁盘"就是 LangGraph state 里的 `files` 字段，`invoke` 不带，就是新开一张空白草稿纸。**没有 SharedState 这种全局变量给你白嫖**。

**Q2：那这破特性有什么用？**
恰恰是优点——**无痕**（跑完即焚，不留垃圾）、**可序列化**（files 快照就是普通 dict，能存 JSON、能跨进程传、能塞进 checkpoint）。
下一章 subagent 会看到：主 Agent 和子 Agent 就是靠把 `files` 快照递来递去实现"共享工作台"的。

**Q3：什么时候该换真磁盘（FilesystemBackend）？**
当你要"关掉进程文件还在"（多轮会话接力、多 Agent 共享、产物要给人类看）时——这正是 03-02 的主题。

## 六、自查清单

- [ ] 能说出"虚拟文件系统"解决的两个痛点：上下文爆炸 + 过程不可追溯
- [ ] 知道 `r["files"]` 是快照，`invoke(files=快照)` 能复活
- [ ] 记住预置文件必须 `{"content": str}` 字典格式
- [ ] 理解 StateBackend = 内存盘：进程内共享、进程外蒸发

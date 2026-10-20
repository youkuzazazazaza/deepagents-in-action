# 第4章作业打卡 · 学有余力：SummarizationMiddleware + TodoList 长跑配合

**验证什么**
把对话拉到 5 轮、trigger 压到 10 条消息（keep 4），让摘要压缩真实触发，观察三件事：① 消息数是不是被"压"住了；② 压缩后旧事实还记得吗；③ todos 和文件这些"结构性记忆"会不会被压坏。

**怎么做的（实验设计）**
- 代码：`code/hw_bonus.py`，`create_deep_agent(backend=FilesystemBackend, checkpointer=InMemorySaver, middleware=[SummarizationMiddleware(model=model, trigger=("messages",10), keep=("messages",4)), TodoListMiddleware()])`
- 两个版本坑（都已标注在代码注释里）：InMemorySaver 要从 `langgraph.checkpoint.memory` 导入（langchain 1.x 里没有 `langchain.checkpoint` 这个模块）；SummarizationMiddleware 的 `model` 是必填首参，摘要由谁来做必须显式指定
- 5 轮对话：T1 核对订单写 report → T2 问明细 → T3 追加新单 A005 → T4 闲聊两句 → T5 突然袭击考旧记忆（A001 多少钱？总额多少？）
- 每轮结束从 checkpointer 的 state 里数消息条数、抄 todos、列文件清单

**实际结果（真实输出摘录）**
```
消息数 T0→T5：0 → 6 → 10 → 8 → 6 → 8     ← 锯齿！10 触发压缩砍回 6
T5 突袭：A001=无线鼠标 299 元 ✓（第1轮的旧事实，压缩后仍在）
        总额 798 ✓（且主动说明 A005 是追加的、未计入）
todos：3 项从 T1 起一直存活，未随压缩丢失
```

**证据与解释**
`evidence/hw_bonus_evidence.json`：`turns_snaps` 存了每轮的 n_msgs/n_todos/todos/files 四元快照；`hw_bonus_report.md` 是 T3 追加后 agent 自己改写的磁盘原件。消息数 10→8→6 的下降证明压缩不止发生在"发给模型的请求"里，**checkpoint 里的 state 本身也被瘦身**；被压掉的是旧对话的逐字记录，关键事实转进了摘要，而 todos/files 这类结构化状态是独立字段，不参与消息压缩。

**下一步修正**
本实验的 InMemorySaver 重启进程就丢。生产上要换成持久化 checkpointer（SqliteSaver/PostgresSaver），跨会话的"记忆连续性"才能成立——这正好衔接后续章节的记忆系统。

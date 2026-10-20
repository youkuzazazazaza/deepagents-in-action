# 第4章作业打卡 · Advanced 挑战级：A/B 对照，量化规划的价与不值

**验证什么**
同一任务、同一数据，唯一变量是"挂不挂 TodoListMiddleware"，各跑一轮，量化对比：工具调用数、token 消耗、耗时、正确性。作业题干里"哪怕结果没改善，能解释原因也算挑战完成"——本组实验正是冲着这句话设计的。

**怎么做的（控制了什么变量）**
- 代码：`code/hw_advanced.py`，A 轮 `middleware=[]`，B 轮 `middleware=[TodoListMiddleware()]`，其余全部相同（temperature=0、两轮各自清场重埋同一套资料、GT 由脚本硬编码）
- 采集方式：从 `result["messages"]` 的 usage_metadata 累加每条 AI 消息的 input/output tokens（坑：usage 里混着嵌套 dict，只累加 int 值）；从 tool_calls 数调用次数
- 数据集换成另一套（GT：dedup 798.00 / payable 768.00 / shipping 0.00），避免和 Basic 记忆串台

**实际结果（真实数字）**
```
            工具调用   token总量    耗时   报告正确  write_todos次数
A 轮 off        6        5,184     7.2s     ✓          0
B 轮 on         6       11,858     7.0s     ✓          0   ← ！
Δ               0        +6,674   -0.2s      -         0
```
B 轮 token 翻了一倍多（+128.7%），**但一次 write_todos 都没调**，工具数、正确性、耗时全无差别。

**证据与解释**
`evidence/hw_advanced_evidence.json`（含两轮 tool_seq / tokens / report_numbers）+ 两份产物原件 `evidence/hw_advanced_report_todo_off.md`、`hw_advanced_report_todo_on.md`（内容完全一致，都是 798/768/0）。两条解释：① 中间件只提供能力，用不用仍由模型决定——多出来的 token 全是系统提示里的计划规程和工具 schema，属"入场费"；② 这种 3 文件+1 产物的短任务，上下文根本长不到"忘事"，规划的收益天然显示不出来。结果没改善，但原因说得清——挑战完成。

**下一步修正**
想让规划的收益显形，得把任务拉长、上下文撑大；同时如果上下文真变长了，又轮到 SummarizationMiddleware 登场——这就是学有余力 Bonus 的舞台。

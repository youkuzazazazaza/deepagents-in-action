# 第4章作业打卡 · Lite 打卡级：亲眼看 todos 走完三段流转

**验证什么**
让 Agent 用 `write_todos` 列一次三步计划（查分 → 算平均 → 写总结），亲眼看到清单状态的三段流转：pending → in_progress → completed。

**怎么做的（观察窗口怎么开）**
- 代码：`code/hw_lite.py`，`create_agent(model, tools=[lookup_score, average], middleware=[TodoListMiddleware()])`
- 关键点 1：v0.7 的 `create_agent` 里 TodoList **不是自带的**，必须显式挂 `middleware=[TodoListMiddleware()]`，否则模型连 `write_todos` 这个工具都看不到
- 关键点 2：todos 是 State 字段，invoke 结束只剩"最终快照"（通常全 completed），三段流转看不全。但 **write_todos 每次被调用的入参（整份清单 JSON）都留在消息流里**——从 transcript 把每次调用的入参抠出来回放，就是完整的生命周期。证据 > 一切

**实际结果（真实输出摘录，非 Agent 转述）**
```
工具调用序列：
  ['write_todos', 'lookup_score', 'lookup_score', 'write_todos',
   'average', 'write_todos', 'write_todos']
第2次 write_todos：            ← 干完第1步后更新
  [  completed] 查小明和小红的分数
  [in_progress] 算两人的平均分
  [    pending] 用一段话总结两位学员的表现
最终 result['todos']：三项全部 completed
```
7 项自检（write_todos_called / saw_pending / saw_in_progress / saw_completed / final_all_completed / lookup_x2 / average_x1）**全 PASS**。

**证据与解释**
`evidence/hw_lite_evidence.json`：`todos_snapshots` 字段存了 4 次调用的完整入参，`tool_seq` 存工具序列，`check` 7 项全 true。分数写死在脚本里（小明 86 / 小红 92 / 平均 89.0），temperature=0，重跑可复现。

**下一步修正**
Lite 只证明了"清单会动"。但清单全勾就等于任务做对了吗？——这正是 Basic 要拆的雷：**计划全部 completed ≠ 验收通过**。

# 第4章作业打卡 · Basic 基础级：计划全勾了，数字对了吗？

**验证什么**
本级的灵魂句：**计划全部 completed ≠ 验收通过**。让 Agent 带着 TodoListMiddleware 做 5 步订单核对任务，最后并排打印「todos 状态表」vs「磁盘核对表」——就算清单全勾，数字错一个，验收就是不过。

**怎么做的（埋了什么雷）**
- 代码：`code/hw_basic.py`，`create_deep_agent(backend=FilesystemBackend(...), middleware=[TodoListMiddleware()])`
- 脚本每轮**清场重埋** 3 份固定资料：orders.csv（故意让 A003 重复出现两行）、promo.txt（满 300 立减 30，每单只享一次）、shipping.txt（不足 100 收 12，满 100 包邮）
- 地面真值 GT 由脚本自己算，不信 Agent：raw 743.50（含重复）/ dedup 598.50 / payable 568.50 / shipping 0.00。去重这步就是"雷"——不去重总额就是 743.50，一错全错
- 核对方式：绕开 Agent，`open()` 直读磁盘上的 report.md，正则抽数字逐项比对

**实际结果（磁盘原文，非 Agent 转述）**
```
==== B. todos 状态表（Agent 自己声称的进度）====
  5 项全部 completed ✓
==== C. 磁盘核对表 ====
  - 去重后订单总额：598.50 元     ← 重复的 A003 被正确只计一次
  - 应付金额：568.50 元           ← 满 300 减 30 只减了一次
  - 运费：0.00 元
==== D. 逐项核对：report_exists / dedup / payable / shipping 全 PASS，verdict=true
```

**证据与解释**
`evidence/hw_basic_evidence.json`：`ground_truth` 与 `got` 并排存档，`checks` 四项全 true，`tool_seq` 共 9 次调用（write_todos 开局 → ls → read_file×3 → write_todos → write_file → read_file → write_todos）。Agent 最终回答里还主动列出了 A003 去重的算式。这轮它真做对了——但注意脚本里的那行提醒：这份确定性来自脚本核对，不是来自清单上的勾。

**下一步修正**
Basic 里"清单全勾+数字全对"只能说明这一轮运气加实力都在线。规划到底**值不值**（成本多少、什么时候有收益）没有量化——这正是 Advanced 的 A/B 对照实验要回答的。

# 任务规划与分解 — 让 Agent 学会拆解复杂任务

1、规划能力：先思考再行动-把大任务拆解为小步骤，然后逐步执行、追踪进度、动态调整。write_todos



2、常见状态流转：pending -> in_progress -> completed



3、Node-style：before_agent、before_model、after_model、after_agent

执行方式：编译成Agent图中的独立节点，按生命周期顺序执行

适合场景：校验、状态变更、审计、人工中断



Wrap-style：wrap_model_call、wrap_tool_call

执行方式：包裹一次模型或工具调用；可以不调用、调用一次或者多次handler

适合场景：重试、缓存、降级、请求或响应转换




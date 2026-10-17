# Task2 - 第三章：虚拟文件系统（Virtual File System）

> 课程地址: https://datawhalechina.github.io/deepagents-in-action/chapters/ch03-virtual-filesystem/
> 本章定位: DeepAgents 的地基。Agent 的所有"记忆"都活在一张虚拟文件系统里，本章把它拆开看个明白。

## 产出物清单

| 类型 | 文件 | 说明 |
|------|------|------|
| 笔记 | notes/01_StateBackend_虚拟文件系统.md | 虚拟文件系统全景 + 内存盘后端 |
| 笔记 | notes/02_Filesystem与Composite_真磁盘分区.md | 三种后端: StateBackend/FilesystemBackend/CompositeBackend |
| 笔记 | notes/03_截断与卸载_大结果治理.md | 大结果治理: 80000字符红线、截断vs卸载 |
| 笔记 | notes/04_权限系统_deny与interrupt.md | 权限系统: 三元组规则、allow/deny/interrupt模式 |
| 笔记 | notes/05_排错手册_源码考古.md | 排错手册: 源码考古路线图 |
| 笔记 | notes/06_打卡心得.md | 本章心得: 一页纸总结 + 常见坑 |
| 实证 | evidence/ | 8个实验文件: 路由前缀验证、截断实测、权限绕过等 |
| 图表 | assets/d1_vfs_overview.svg/.png | 虚拟文件系统全景图 |
| 图表 | assets/d2_backends.svg/.png | 三种后端对比图 |
| 图表 | assets/d3_eviction.svg/.png | 大结果治理流程图 |
| 图表 | assets/d4_permission.svg/.png | 权限决策流程图 |
| 源码 | assets/src/*.json | 图表可编辑源码(fireworks-tech-graph) |
| 实验 | code/ | 4个lab的完整可运行代码 |

## 章节主线（大白话版）

1. **一张文件系统 = Agent 的工作记忆**: Agent 不靠"脑内缓存"，读写文件就是它记事的方式。
2. **三个后端随便换**: 内存盘(快、重启就没)、真磁盘(慢一点、能存档)、组合盘(分区挂载，取两者所长)。
3. **子Agent共享同一张盘**: 隔离靠"前缀路由"，不是复制一份盘——省内存又能协作。
4. **输出大了要治理**: 超过 80000 字符的结果会被拦下——读文件给你"截断+提示"，其它工具干脆"卸载+取件条"。
5. **权限三模式**: allow 放行 / deny 拒绝 / interrupt 问人。deny 是"看得见的墙"，真正的安全靠 interrupt。

## 关键实证结论（evidence 摘要）

- `routes` 是**前缀匹配**不是 glob；只有权限规则里的路径才是 glob（lab1）
- 红线 = 80000 字符 ≈ 20000 token × 4（lab3）
- `read_file` 必须**显式传大 limit** 才触发截断提示（lab3）
- 其它工具超线结果被卸载成文件，返回 1377 字符的"取件条"（lab3）
- `files` 预置文件结构是 `{"content": str}`（lab1）
- deny 拒绝时 Agent 能看到拒绝原因，可能"绕道"——所以安全敏感操作用 interrupt（lab4）
- interrupt 会让 Agent 暂停并吐出 `__interrupt__` 事件等待人工确认（lab4）

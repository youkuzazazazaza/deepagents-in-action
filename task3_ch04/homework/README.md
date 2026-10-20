# 第4章作业包：Todo 规划与上下文压缩实战

三个难度档 + 学有余力，全部真机跑通（WSL Ubuntu + deepseek-flash，deepagents 0.7.x / langchain 1.0 agent 栈），证据全部落盘可复现。

## 目录
```
code/    hw_lite.py       打卡级：write_todos 列一次计划，亲眼看三段流转
         hw_basic.py      基础级：清单全勾 ≠ 验收通过（埋雷订单 + 磁盘核对）
         hw_advanced.py   挑战级：Todo 开/关两轮 A/B 对照，量化规划的价与不值
         hw_bonus.py      学有余力：Summarization × Todo，压缩后清单还活着吗
notes/   hw_lite_daka.md 等 4 份打卡笔记（验证什么/怎么做的/实际结果/证据与解释/下一步）
         hw_lite_teach.md 等 4 份教学详解（完整代码全注释 + 大白话逐段拆解 + 真实输出摘录 + 踩坑 + 一句话记住）
evidence/ 4 份 *_evidence.json + advanced 两轮 report 原件 + bonus report 原件
```

## 一键复现（WSL）
```bash
mkdir -p /root/ch04_hw && cd /root/ch04_hw
V=/root/research_deepagent/.venv/bin/python
for s in hw_lite hw_basic hw_advanced hw_bonus; do
  $V /mnt/d/gitcode/learn/deepagents-in-action/task3_ch04/homework/code/$s.py
done
# lite 打 7 项自检全 PASS；basic 判定表 4/4 + verdict=true；
# advanced 两轮均 correct；bonus 裁判全 True；证据 json 生成在当前目录
```

## 踩坑提醒（本包实测）
- v0.7 的 `create_agent` **不带** TodoList，必须显式 `middleware=[TodoListMiddleware()]`，否则模型连 write_todos 工具都看不到
- 看生命周期别只看 `result["todos"]`（最终快照通常已全 completed），要抠 transcript 里每次 write_todos 的**入参**
- A/B 对照必须：TASK 文案对规划只字不提 + 每轮清场重埋 + temperature=0，三缺一就变量污染
- `SummarizationMiddleware(model=model, trigger=("messages",10), keep=("messages",4))`——model 必传（摘要是一次 LLM 调用）；多轮对话须挂 checkpointer + thread_id
- 观察真实库存用 `agent.get_state(cfg)`，不是 invoke 返回值

## 实验结论速查
| 档位 | 实验问题 | 一句话结论 |
|---|---|---|
| Lite | 清单会动吗 | pending→in_progress→completed 三段流转全程留痕（4 次快照） |
| Basic | 全勾=做对吗 | 598.50/568.50/0 全对靠磁盘核对，勾只是自我声明 |
| Advanced | 规划值多少 | B 轮 token +6674、write_todos 0 次：短任务只收入场费 |
| Bonus | 压缩咬掉什么 | 消息 6→10→8→6→8 锯齿，todos/磁盘/关键事实全存活 |

关联正文实验：`../labs/`（lab1 todo 生命周期探针、lab2 中间件开关对照、lab3/4 深度代理与规划、lab5 摘要压缩）。

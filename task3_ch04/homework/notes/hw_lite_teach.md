# 第4章作业·Lite 打卡级 教学详解：亲眼看 todos 从 pending 走到 completed

## 一、这一关到底在考什么

一句话：让 Agent 干一件三步小活，你要**亲眼看到清单状态的三段流转**——pending（待办）→ in_progress（进行中）→ completed（完成）。

看什么容易，怎么看才是门槛。todos 是 Agent State 里的一个字段，`invoke()` 一返回，你手里只剩"最终快照"——通常已经全 completed 了，中间过程像没发生过。这关真正教你的观察术是：**write_todos 每次被调用，它的入参（整份清单 JSON）都会原样留在消息流里**。把每次调用的入参抠出来排成一列，生命周期就自己"回放"出来了。

比喻：todos 字段是"黑板最后一次擦完的样子"，而 transcript 里的 write_todos 入参是"监控录像"。快照只有一帧，录像才有全片。

还有个前置知识点：v0.7 的 `create_agent` 里，TodoList **不是自带的**。不显式挂 `middleware=[TodoListMiddleware()]`，模型连 `write_todos` 这个工具都看不见——这一步漏了，后面全白搭。

## 二、完整代码（注释齐全）

```python
# ============================================================
# 【第4章 作业·Lite 打卡级】write_todos 列一次计划，
#           亲眼看 todos 从 pending 走到 completed
# ============================================================
# 打卡要求：让 Agent 用 write_todos 列一次计划，亲眼看到
# 清单状态的三段流转：pending（待办）→ in_progress（进行中）
# → completed（完成）。
#
# 观察窗口怎么开？todos 是 Agent State 里的独立字段，
# invoke 结束后只剩"最终快照"（通常全 completed）。
# 但 write_todos 每次被调用，它的参数（整份清单 JSON）都会
# 留在消息流里 —— 所以从 transcript 里把每一次 write_todos
# 的入参抠出来，就能回放整个生命周期。证据 > 一切。
#
# 跑法（WSL）：
#   mkdir -p /root/ch04_hw && cd /root/ch04_hw && /root/research_deepagent/.venv/bin/python \
#       /mnt/d/gitcode/learn/deepagents-in-action/task3_ch04/homework/code/hw_lite.py
# ============================================================
import os, json

# ---------- 第 0 步：加载 .env（Key 绝不明文写） ----------
def load_env(p):
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env("/root/research_deepagent/.env")

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
    max_retries=2,
    temperature=0,          # 固定输入 → 尽量可复现
)

# ---------- 两个"成绩册"工具：返回值写死，好核对 ----------
_SCORES = {"小明": 86, "小红": 92}

def lookup_score(name: str) -> int:
    """查学员分数。name 只支持：小明、小红。"""
    print(f"    [工具执行] lookup_score({name!r}) -> {_SCORES.get(name)}")
    return _SCORES[name]

def average(a: int, b: int) -> float:
    """求两个数的平均分。"""
    r = (a + b) / 2
    print(f"    [工具执行] average({a}, {b}) -> {r}")
    return r

# ---------- 显式启用 TodoListMiddleware（v0.7 不是自带的！） ----------
agent = create_agent(
    model=model,
    tools=[lookup_score, average],
    middleware=[TodoListMiddleware()],   # ← 显式挂上，write_todos 才存在
)

TASK = (
    "帮我完成一份学员小卡，共3步：\n"
    "1) 查小明和小红的分数；\n"
    "2) 算两人的平均分；\n"
    "3) 用一段话总结两位学员的表现（分数要写进总结里）。\n"
    "开工前请先用 write_todos 把这3步列计划；"
    "每完成一步就更新一次清单状态，全部做完再回答。"
)

result = agent.invoke({"messages": [{"role": "user", "content": TASK}]})

# ---------- 从 transcript 抠出每一次 write_todos 的入参 ----------
snapshots = []          # 每次调用时的整份清单（回放生命周期的"录像"）
tool_seq = []           # 工具调用序列（按发生顺序）
for m in result["messages"]:
    if m.type == "ai" and getattr(m, "tool_calls", None):
        for tc in m.tool_calls:
            tool_seq.append(tc["name"])
            if tc["name"] == "write_todos":
                todos_arg = tc["args"].get("todos")
                snapshots.append([{"content": t.get("content"),
                                   "status": t.get("status")} for t in todos_arg])

print("==== A. 工具调用序列 ====")
print(" ", tool_seq)

print("\n==== B. todos 生命周期回放（每次 write_todos 的入参）====")
for i, snap in enumerate(snapshots, 1):
    print(f"  第{i}次 write_todos：")
    for t in snap:
        print(f"    [{t['status']:>11s}] {t['content']}")

final_todos = result.get("todos")
print("\n==== C. 最终 result['todos']（State 字段快照）====")
print(json.dumps(final_todos, ensure_ascii=False, indent=2))

final_answer = str(result["messages"][-1].content)
print("\n==== D. 最终回答（前200字）====")
print(" ", final_answer[:200])

# ---------- 打卡自检：三段流转是否都亲眼看到了 ----------
statuses_seen = {t["status"] for snap in snapshots for t in snap}
check = {
    "write_todos_called": len(snapshots) >= 2,
    "saw_pending": "pending" in statuses_seen,
    "saw_in_progress": "in_progress" in statuses_seen,
    "saw_completed": "completed" in statuses_seen,
    "final_all_completed": bool(final_todos) and all(
        t["status"] == "completed" for t in final_todos),
    "lookup_x2": tool_seq.count("lookup_score") == 2,
    "average_x1": tool_seq.count("average") == 1,
}
print("\n==== E. 打卡自检 ====")
for k, v in check.items():
    print(f"  {'PASS' if v else 'FAIL':4s}  {k}")

ev = {"task": TASK, "tool_seq": tool_seq,
      "todos_snapshots": snapshots, "final_todos": final_todos,
      "final_answer_head": final_answer[:300], "check": check}
with open("hw_lite_evidence.json", "w", encoding="utf-8") as f:
    json.dump(ev, f, ensure_ascii=False, indent=2)
print("\n证据已存 /root/ch04_hw/hw_lite_evidence.json")
print("DONE")
```

## 三、逐段拆解（大白话）

**为什么 temperature=0**：打卡要的是"可复现"。分数写死、采样关掉，谁跑都是同一条轨迹。

**为什么显式挂 TodoListMiddleware**：v0.7 的 `create_agent` 默认**不带**规划。书里"开箱即用"的写法对应的是 `create_deep_agent` 那一族（它内部把全家桶装好了）；裸 `create_agent` 想要 todos，就得自己挂中间件。挂上之后发生两件事：① State 多出一个 `todos` 字段；② 模型的工具列表多出一个 `write_todos`。

**回放生命周期是全篇最值钱的一段**：`for m in result["messages"]` 遍历的是"消息录像带"，每条 AI 消息带着 `tool_calls`；遇到 `write_todos` 就把它的入参整份摘下来。四次调用入参排在一起，正好连成 pending→in_progress→completed 的**全片**。这招在后面 Basic/Advanced/Bonus 全部复用——transcript 是一切实验的物证来源。

**自检七项**在防什么：防"Agent 嘴上列了计划实际没动工具"（write_todos_called≥2）、防"没见到中间状态就宣布通关"（saw_pending/in_progress/completed 三项分开判）、防"清单全勾但活没干完"（lookup_x2 + average_x1）。

## 四、跑起来长什么样（真实输出摘录）

```text
==== A. 工具调用序列 ====
  ['write_todos', 'lookup_score', 'lookup_score', 'write_todos',
   'average', 'write_todos', 'write_todos']

==== B. todos 生命周期回放（每次 write_todos 的入参）====
  第1次 write_todos：            ← 三步全是 pending（刚立项）
    [    pending] 查小明和小红的分数
    [    pending] 算两人的平均分
    [    pending] 总结两位学员的表现
  第2次 write_todos：            ← 查分完成 → in_progress 推进一格
    [  completed] 查小明和小红的分数
    [in_progress] 算两人的平均分
    [    pending] 总结两位学员的表现
  第3次 write_todos：            ← 平均分完成
    [  completed] 查小明和小红的分数
    [  completed] 算两人的平均分
    [in_progress] 总结两位学员的表现
  第4次 write_todos：            ← 全部 completed（收工）
    [  completed] 查小明和小红的分数
    [  completed] 算两人的平均分
    [  completed] 总结两位学员的表现

==== E. 打卡自检 ====
  PASS  write_todos_called
  PASS  saw_pending
  PASS  saw_in_progress
  PASS  saw_completed
  PASS  final_all_completed
  PASS  lookup_x2
  PASS  average_x1
```

最终回答里两位学员的分数（86 / 92）和平均分（89.0）都写进了总结——分数是从工具返回值来的，不是模型编的。

## 五、这一关的坑

1. **不挂中间件 = 白跑**：忘了 `middleware=[TodoListMiddleware()]`，模型没有 write_todos 工具，会直接口头答题，自检第一项就 FAIL。
2. **invoke 后只看 result['todos'] 看不到过程**：那是最终快照，通常已全 completed。想看三段流转，必须去 transcript 里抠每次 write_todos 的入参。
3. **m.type 判断**：transcript 里既有 dict 也有 AIMessage 对象，判 `m.type == "ai"` 比 isinstance 稳；`tool_calls` 可能不存在，用 `getattr(..., None)` 兜住。

## 六、一句话记住

**快照只有一帧，录像才有全片——规划的生命周期藏在每次 write_todos 的入参里。**

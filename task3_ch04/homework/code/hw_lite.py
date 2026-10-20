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
    "开工前请先用 write_todos 把这3步列成计划；"
    "每完成一步就更新一次清单状态，全部做完再回答。"
)

result = agent.invoke({"messages": [{"role": "user", "content": TASK}]})

# ---------- 从 transcript 抠出每一次 write_todos 的入参 ----------
snapshots = []          # 每次调用时的整份清单
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

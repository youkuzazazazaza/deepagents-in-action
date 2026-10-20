# ============================================================
# 【第4章 Lab1】TodoListMiddleware：给 Agent 发一本"任务便签本"
# ============================================================
# 一句话：write_todos 不是天生的，是 TodoListMiddleware 塞进来的。
#   - 不加中间件：Agent 没有 write_todos 工具，也没有 todos 状态
#   - 加了：多出 write_todos 工具 + todos 状态字段 + 一段"先规划再干"的提示词
#   - todos 三个状态：pending(待办) → in_progress(进行中) → completed(完成)
#
# 跑法（WSL）：
#   mkdir -p /root/ch04_labs && /root/research_deepagent/.venv/bin/python \
#       /mnt/d/gitcode/learn/deepagents-in-action/task3_ch04/code/lab1_todo_lifecycle.py \
#       | tee /root/ch04_labs/lab1_out.txt
# ============================================================
import os, json

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
)

# ---------- 第 1 步：离线对比（不花 token）----------
bare = create_agent(model=model, tools=[], middleware=[])
with_todo = create_agent(model=model, tools=[], middleware=[TodoListMiddleware()])
print("==== A. 图节点对比（离线）====")
print("裸 create_agent          :", list(bare.get_graph().nodes.keys()))
print("+ TodoListMiddleware     :", list(with_todo.get_graph().nodes.keys()))
print()
print("解读：")
print("  - 裸 agent 连 tools 节点都没有（没有工具可调用）")
print("  - 加 TodoList 后多出 tools 节点（write_todos 工具挂这儿）")
print("  - 还多出 TodoListMiddleware.after_model：模型每次说话后")
print("    它负责把 todos 状态同步进 Agent State")

# ---------- 第 2 步：实跑一个"必须规划"的小任务 ----------
def roll_dice(sides: int = 6) -> int:
    """掷一次骰子，返回 1~sides 的随机数。"""
    import random
    n = random.randint(1, sides)
    print(f"    [工具执行] roll_dice(sides={sides}) -> {n}")
    return n

def make_agent(use_todo: bool):
    mw = [TodoListMiddleware()] if use_todo else []
    return create_agent(model=model, tools=[roll_dice], middleware=mw)

TASK = ("请完成一个小实验，共3步：1) 掷一次6面骰子；2) 再掷一次；"
        "3) 汇总两次点数之和。如果你有 write_todos 工具，"
        "请先用它制定计划再执行；没有就直接做。")

def run_once(tag: str, use_todo: bool):
    print(f"\n==== B. {tag} ====")
    agent = make_agent(use_todo)
    result = agent.invoke({"messages": [{"role": "user", "content": TASK}]})
    tool_calls = []
    for m in result["messages"]:
        if m.type == "ai" and getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                tool_calls.append(tc["name"])
    print(f"  实际调用工具序列: {tool_calls}")
    print(f"  write_todos 被调用次数: {tool_calls.count('write_todos')}")
    todos = result.get("todos")
    print(f"  result['todos'] = {json.dumps(todos, ensure_ascii=False) if todos else todos}")
    final = result["messages"][-1].content
    print(f"  最终回答(前120字): {str(final)[:120]}")
    return {"tag": tag, "tool_calls": tool_calls, "todos": todos,
            "write_todos_count": tool_calls.count("write_todos"),
            "has_todos_state": todos is not None,
            "final_head": str(final)[:200]}

runs = []
runs.append(run_once("B1: 不加 TodoList（对照组）", use_todo=False))
runs.append(run_once("B2: 加 TodoListMiddleware（实验组）", use_todo=True))

# ---------- 第 3 步：小结证据 ----------
print("\n==== C. 对照结论 ====")
for r in runs:
    print(f"[{r['tag']}] 工具={r['tool_calls']} | write_todos×{r['write_todos_count']}"
          f" | todos状态字段={'有' if r['has_todos_state'] else '无'}")
print("""
大白话总结：
  - write_todos 是"外挂"不是"自带"：v0.7 里必须显式加 TodoListMiddleware
  - todos 保存在 Agent State（图的独立字段），不是普通消息
  - 三状态流转 pending → in_progress → completed 由模型自己维护
  - 教学提醒：清单"画勾"不等于真做完，要对照产物检查
""")

with open("/root/ch04_labs/lab1_evidence.json", "w", encoding="utf-8") as f:
    json.dump(runs, f, ensure_ascii=False, indent=2)
print("证据已存 /root/ch04_labs/lab1_evidence.json")

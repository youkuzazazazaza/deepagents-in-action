# ============================================================
# 【第4章 Lab2】todos 的持久化：Checkpointer + thread_id 缺一不可
# ============================================================
# 一句话：todos 活在 Agent State 里，invoke 一结束就"人走茶凉"；
#   想让下次接着用，必须给 agent 配 Checkpointer，并且两次用同一个
#   thread_id。换一个 thread_id = 开一个新会话，todos 清零。
#
# 跑法（WSL）：
#   /root/research_deepagent/.venv/bin/python \
#     /mnt/d/gitcode/learn/deepagents-in-action/task3_ch04/code/lab2_todo_persistence.py \
#     | tee /root/ch04_labs/lab2_out.txt
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
from langgraph.checkpoint.memory import InMemorySaver

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
    max_retries=2,
)

def shout(text: str) -> str:
    """把文本转成大写并感叹（模拟'完成一步任务'）。"""
    return text.upper() + "!"

ev = {"rounds": []}

def snap(tag, config):
    st = agent.get_state(config)
    todos = st.values.get("todos")
    n_msg = len(st.values.get("messages", []))
    rec = {"tag": tag, "todos": todos, "n_messages": n_msg}
    ev["rounds"].append(rec)
    print(f"  [{tag}] todos状态快照: n_messages={n_msg}")
    for t in (todos or []):
        print(f"      - {t['status']:11s} {t['content']}")
    if not todos:
        print("      (无 todos)")
    return rec

# ---------- 实验一：没有 Checkpointer ----------
print("==== 实验一：不配 Checkpointer，连续 invoke 两次 ====")
agent = create_agent(model=model, tools=[shout], middleware=[TodoListMiddleware()])
PLAN = ("请用 write_todos 制定3步计划：1)大声喊'早安' 2)大声喊'午安' 3)大声喊'晚安'。"
        "本轮只执行第1步。")
r1 = agent.invoke({"messages": [{"role": "user", "content": PLAN}]})
print(f"  第1次 invoke 后 result['todos']: {json.dumps(r1.get('todos'), ensure_ascii=False)}")
r2 = agent.invoke({"messages": [{"role": "user", "content": "继续，执行剩下两步。"}]})
print(f"  第2次 invoke 后 result['todos']: {json.dumps(r2.get('todos'), ensure_ascii=False)}")
print("  --> 没有记忆：第2次根本不记得有计划，todos 丢了\n")
ev["no_checkpointer"] = {"first": r1.get("todos"), "second": r2.get("todos")}

# ---------- 实验二：Checkpointer + 同一个 thread_id ----------
print("==== 实验二：InMemorySaver + thread_id='user-001' ====")
saver = InMemorySaver()
agent = create_agent(model=model, tools=[shout],
                     middleware=[TodoListMiddleware()], checkpointer=saver)
cfg = {"configurable": {"thread_id": "user-001"}}

agent.invoke({"messages": [{"role": "user", "content": PLAN}]}, config=cfg)
snap("同线程·第1轮后", cfg)
agent.invoke({"messages": [{"role": "user", "content": "继续，执行剩下两步。"}]}, config=cfg)
snap("同线程·第2轮后", cfg)

# ---------- 实验三：换一个 thread_id ----------
print("==== 实验三：换 thread_id='user-002'（新会话） ====")
cfg2 = {"configurable": {"thread_id": "user-002"}}
agent.invoke({"messages": [{"role": "user", "content": "我们的计划进行到哪一步了？"}]}, config=cfg2)
snap("新线程·第1轮后", cfg2)

# ---------- 结论 ----------
print("""
大白话总结：
  1) Agent State 是"一次性"的：invoke 结束即丢（实验一）
  2) Checkpointer 像存档机：把 messages + todos 一起存下来
  3) thread_id 是存档槽位号：同一个号才能读同一个存档
  4) 生产上用 SqliteSaver/PostgresSaver 替换 InMemorySaver，
     重启进程也不丢（第8章细讲）
""")

with open("/root/ch04_labs/lab2_evidence.json", "w", encoding="utf-8") as f:
    json.dump(ev, f, ensure_ascii=False, indent=2)
print("证据已存 /root/ch04_labs/lab2_evidence.json")

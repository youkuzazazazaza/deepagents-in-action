# ============================================================
# 【第4章 Lab3】SummarizationMiddleware：自动摘要 + todos 锚定实验
# ============================================================
# 一句话：聊天记录太长会被"压缩存档"，但 todos 是独立字段，
#   不会被摘要吃掉——这就是"规划作为锚"的含义。
# 关键参数（v0.7.8 实测签名）：
#   DA 版: SummarizationMiddleware(model, *, backend=必填!,
#         trigger=None 默认不触发!, keep=('messages',20), ...)
#   LC 版: SummarizationMiddleware(model, *, trigger=None, ...)
#   --> 手动实例化 DA 版必须自己传 backend，且必须设 trigger，
#       否则它"在场"但永远不动手（默认 trigger=None）。
#
# 跑法（WSL）：
#   /root/research_deepagent/.venv/bin/python \
#     /mnt/d/gitcode/learn/deepagents-in-action/task3_ch04/code/lab3_summarization_anchor.py \
#     | tee /root/ch04_labs/lab3_out.txt
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
from deepagents.middleware import SummarizationMiddleware, FilesystemMiddleware
from deepagents.backends import StateBackend

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
    max_retries=2,
)

def shout(text: str) -> str:
    """把文本转成大写并感叹（制造一来一回的消息）。"""
    return text.upper() + "!"

ev = {}

def n_msg(st):
    return len(st.values.get("messages", []))

# ---------- 对照组：没有摘要，消息无限增长 ----------
print("==== 对照组：只有 TodoList，没有摘要中间件 ====")
ctl = create_agent(model=model, tools=[shout], middleware=[TodoListMiddleware()],
                   checkpointer=__import__("langgraph.checkpoint.memory",
                                           fromlist=["InMemorySaver"]).InMemorySaver())
cfg = {"configurable": {"thread_id": "ctl"}}
ctl.invoke({"messages": [{"role": "user", "content":
    "用 write_todos 建计划：1)喊'一号' 2)喊'二号' 3)喊'三号'，然后只做第1步。"}]}, config=cfg)
counts = [n_msg(ctl.get_state(cfg))]
for word in ["二号", "三号"]:
    ctl.invoke({"messages": [{"role": "user", "content": f"继续，大声喊'{word}'。"}]}, config=cfg)
    counts.append(n_msg(ctl.get_state(cfg)))
print(f"  消息数逐轮增长: {counts}")
print("  --> 没人管聊天记录，只会越滚越长\n")
ev["control_msg_counts"] = counts

# ---------- 实验组：Filesystem + TodoList + Summarization ----------
print("==== 实验组：手动组装三件套，trigger=('messages', 10) ====")
backend = StateBackend()
agent = create_agent(
    model=model, tools=[shout],
    middleware=[
        FilesystemMiddleware(backend=backend),
        TodoListMiddleware(),
        SummarizationMiddleware(model=model, backend=backend,
                                trigger=("messages", 10), keep=("messages", 2)),
    ],
    checkpointer=__import__("langgraph.checkpoint.memory",
                            fromlist=["InMemorySaver"]).InMemorySaver(),
)
cfg2 = {"configurable": {"thread_id": "exp"}}
agent.invoke({"messages": [{"role": "user", "content":
    "用 write_todos 建计划：1)喊'一号' 2)喊'二号' 3)喊'三号'，然后只做第1步。"}]}, config=cfg2)
track = [("round1", n_msg(agent.get_state(cfg2)))]
for word in ["二号", "三号", "再来一次喊'三号'", "喊'加班'"]:
    agent.invoke({"messages": [{"role": "user", "content": f"继续，{word}。"}]}, config=cfg2)
    track.append((word[:6], n_msg(agent.get_state(cfg2))))
print(f"  消息数轨迹: {track}")
peak = max(c for _, c in track)
final = agent.get_state(cfg2)
final_n = n_msg(final)
print(f"  峰值 {peak} 条 → 最终 {final_n} 条"
      f"{'（被摘要压缩了！）' if final_n < peak else '（未触发？）'}")

# 摘要写进了 Backend：看看 files 里有什么
files = final.values.get("files", {})
print(f"  Backend 里的文件: {list(files.keys())}")
hist = [k for k in files if "conversation" in k.lower() or "history" in k.lower()]
ev["msg_track"] = track
ev["files_keys"] = list(files.keys())
if hist:
    content = files[hist[0]]
    content = content["content"] if isinstance(content, dict) else content
    print(f"  找到历史存档: {hist[0]}（前300字）")
    print("  " + content[:300].replace("\n", "\n  "))
    ev["history_head"] = content[:600]

# 关键验证：todos 还在吗？
todos = final.values.get("todos")
print(f"\n  压缩后 todos: {json.dumps(todos, ensure_ascii=False)}")
print("  --> 摘要只动 messages，todos 是独立字段，稳如泰山")
ev["todos_after_summary"] = todos

print("""
大白话总结：
  1) DA 版摘要必须手动传 backend + 设 trigger（默认 None=装了不干活）
  2) 触发后旧消息被摘要替换，原文写进 Backend 文件（conversation_history）
  3) todos 是独立状态字段，摘要吃不掉它——长任务里它是"定海神针"
  4) keep=('messages',2) 表示最后2条原样保留
""")

with open("/root/ch04_labs/lab3_evidence.json", "w", encoding="utf-8") as f:
    json.dump(ev, f, ensure_ascii=False, indent=2)
print("证据已存 /root/ch04_labs/lab3_evidence.json")

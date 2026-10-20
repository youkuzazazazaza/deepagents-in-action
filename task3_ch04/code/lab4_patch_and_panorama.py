# ============================================================
# 【第4章 Lab4】PatchToolCallsMiddleware：悬空工具调用的"保险丝"
#              + 中间件全景图（谁加了什么工具/什么节点）
# ============================================================
# 背景：如果消息历史里有一条 AI 的 tool_call 却没有对应的
#   ToolMessage 结果（进程崩溃/人为拼接历史），下次请求模型会
#   直接报错。deepagents 全家桶默认带 PatchToolCallsMiddleware，
#   它会自动补一条 ToolMessage("中断了") 把故事圆上。
#   但 create_agent 造的裸 agent 没有这层保险。
#
# 跑法（WSL）：
#   /root/research_deepagent/.venv/bin/python \
#     /mnt/d/gitcode/learn/deepagents-in-action/task3_ch04/code/lab4_patch_and_panorama.py \
#     | tee /root/ch04_labs/lab4_out.txt
# ============================================================
import os, json, traceback

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
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from deepagents.middleware import SummarizationMiddleware, FilesystemMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.backends import StateBackend

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
    max_retries=2,
)

def shout(text: str) -> str:
    """把文本转成大写并感叹。"""
    return text.upper() + "!"

ev = {}

# ---------- 实验一：悬空 tool_call ----------
dangling = [
    {"role": "user", "content": "请大声喊'你好'"},
    AIMessage(content="", tool_calls=[
        {"name": "shout", "args": {"text": "你好"}, "id": "call_dangling_1"},
    ]),
    # 注意：这里故意"丢了" shout 的 ToolMessage 结果
    {"role": "user", "content": "现在告诉我：上一条工具的结果是什么？"},
]

print("==== 实验一：消息历史里有一条'悬空'的 tool_call ====")
for tag, mws in [("裸 agent（无保险丝）", []),
                 ("+ PatchToolCallsMiddleware（有保险丝）", [PatchToolCallsMiddleware()])]:
    try:
        ag = create_agent(model=model, tools=[shout], middleware=mws)
        r = ag.invoke({"messages": dangling})
        msgs = r["messages"]
        patched = [m for m in msgs if isinstance(m, ToolMessage)
                   and m.tool_call_id == "call_dangling_1"]
        print(f"[{tag}] 正常返回 ✓")
        print(f"   共 {len(msgs)} 条消息; 悬空id的ToolMessage: "
              f"{'有,内容=' + repr(patched[0].content)[:60] if patched else '无'}")
        ev[tag] = {"ok": True, "n_msgs": len(msgs),
                   "patched_content": patched[0].content if patched else None}
    except Exception as e:
        print(f"[{tag}] 报错 ✗  {type(e).__name__}: {str(e)[:160]}")
        ev[tag] = {"ok": False, "err": f"{type(e).__name__}: {str(e)[:300]}"}
print()

# ---------- 实验二：中间件全景表（离线，不花token） ----------
print("==== 实验二：中间件全景表（各自带来什么） ====")
backend = StateBackend()
panorama = [
    ("(空) 裸 create_agent", []),
    ("TodoListMiddleware", [TodoListMiddleware()]),
    ("FilesystemMiddleware", [FilesystemMiddleware(backend=backend)]),
    ("SummarizationMiddleware(DA版)",
     [SummarizationMiddleware(model=model, backend=StateBackend(),
                              trigger=("messages", 30))]),
    ("PatchToolCallsMiddleware", [PatchToolCallsMiddleware()]),
]
rows = []
for name, mws in panorama:
    ag = create_agent(model=model, tools=[shout], middleware=mws)
    nodes = sorted(ag.get_graph().nodes.keys())
    tools_names = []
    for mw in mws:
        ts = getattr(mw, "tools", None) or []
        tools_names += [getattr(t, "name", str(t)) for t in ts]
    rows.append({"middleware": name, "nodes": nodes, "extra_tools": tools_names})
    print(f"[{name}]")
    print(f"   新增工具: {tools_names if tools_names else '(无)'}")
    print(f"   图节点: {nodes}")
ev["panorama"] = rows

print("""
大白话总结：
  1) 悬空 tool_call = 历史里的"烂尾楼"，模型看到会拒收（报错）
  2) PatchToolCallsMiddleware 自动补 ToolMessage("中断")，把楼封顶
  3) deepagents 全家桶默认带它；自己 create_agent 组装时要记得加
  4) 全景表：TodoList→write_todos工具+after_model节点；
     Filesystem→8个ls/cat/write...工具；Summarization→不改图结构
     （藏在 model 调用的包裹层里）；Patch→before_agent节点
""")

with open("/root/ch04_labs/lab4_evidence.json", "w", encoding="utf-8") as f:
    json.dump(ev, f, ensure_ascii=False, indent=2)
print("证据已存 /root/ch04_labs/lab4_evidence.json")

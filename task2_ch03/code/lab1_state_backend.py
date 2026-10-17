# ============================================================
# 【第3章 Lab1】StateBackend（默认后端）：内存里的"草稿本"
# ============================================================
# 一句话：默认后端把文件存在 LangGraph 的 Agent State 里。
#   - 同一次 invoke 里：写完肯定能读回（工具间共享同一个 state）
#   - invoke 结束后：state 不带回存 → 新 invoke 里文件"没了"
#   - 想延续？把上次的 files 塞回去（手动接力）
#
# 跑法（WSL）：
#   cd /root/ch03_labs && /root/research_deepagent/.venv/bin/python \
#       /mnt/d/gitcode/learn/deepagents-in-action/task2_ch03/code/lab1_state_backend.py
# ============================================================
import os, json

# ---------- 第 0 步：加载 .env（和第2章完全一样，Key 绝不明文写） ----------
def load_env(p):
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env("/root/research_deepagent/.env")

from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent   # 默认 backend=StateBackend，不用写

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
    max_retries=2,
)
agent = create_deep_agent(model=model)

def show(title, result):
    """打印消息轨迹 + files（虚拟文件系统的"磁盘"快照）"""
    print(f"\n==== {title} ====")
    print("---- messages 轨迹 ----")
    for m in result["messages"]:
        typ, name = m.type, (m.name or "")
        head = str(m.content)[:90].replace("\n", " ")
        print(f"- {typ:10s} {name:12s} {head!r}")
    print("---- files（虚拟磁盘快照）----")
    for path, meta in (result.get("files") or {}).items():
        data = meta if isinstance(meta, str) else meta.get("content", meta)
        print(f"[file] {path}  ({len(str(data))} chars)")
    if not (result.get("files") or {}):
        print("(空 —— 一个文件都没有)")

# ---------- 第 1 步：让 Agent 写文件 + 读回来（同一次 invoke） ----------
q1 = ("请严格按顺序使用工具：1) write_file 把内容 '- [ ] 买牛奶\n- [ ] 写周报' "
      "写入 /workspace/todo.md；2) read_file 读回 /workspace/todo.md；"
      "3) ls 列出 /workspace。最后告诉我 todo.md 里第一行是什么。")
r1 = agent.invoke({"messages": [{"role": "user", "content": q1}]})
show("第1轮：写→读→列（应看到 todo.md）", r1)

# ---------- 第 2 步：新开一轮（不带 files）→ 文件丢失！ ----------
q2 = "用 ls 列出 /workspace 下的所有文件，并逐个 read_file 它们。现在里面有什么？"
r2 = agent.invoke({"messages": [{"role": "user", "content": q2}]})
show("第2轮：全新 invoke（没带 files）→ 草稿本被撕了", r2)

# ---------- 第 3 步：手动接力（把 r1 的 files 带上）→ 文件复活 ----------
r3 = agent.invoke({
    "messages": [{"role": "user", "content": "用 read_file 读取 /workspace/todo.md，原样告诉我全部内容。"}],
    "files": r1["files"],          # ← 关键：上一轮的虚拟磁盘整个传回来
})
show("第3轮：带上 files 接力 → 文件复活", r3)

# ---------- 存证据 ----------
json.dump({k: v for k, v in r1.items() if k != "messages"},
          open("lab1_r1_files.json", "w"), ensure_ascii=True, indent=1, default=str)
print("\n[SAVED] lab1_r1_files.json")
print("DONE" if "买牛奶" in str(r3.get("files")) else "CHECK_R3")

# ============================================================
# 【第3章 作业·学有余力】第三角 StoreBackend：
#        State / Filesystem / Store 三后端三角对比
# ============================================================
# StoreBackend 把文件放进 LangGraph 的 BaseStore（键值库）：
#   - 按 namespace（命名空间）分格，跨 invoke、跨 Agent 实例、跨 thread 都在
#   - 生命周期 = store 实例本身：换一个新 store（比如重启进程没接持久库）就全丢
# 三角看点：
#   State      存在 Agent State 里 → 一次 invoke（不带 files 接力就没）
#   Filesystem 存在磁盘上         → 文件在就在
#   Store      存在键值库里       → store 在就在（生产上接 Postgres/Redis）
#
# 跑法（WSL）：
#   cd /root/ch03_hw && /root/research_deepagent/.venv/bin/python \
#       /mnt/d/gitcode/learn/deepagents-in-action/task2_ch03/homework/code/hw_bonus_store.py
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
from langgraph.store.memory import InMemoryStore
from deepagents import create_deep_agent
from deepagents.backends import StoreBackend, FilesystemBackend

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
    max_retries=2,
)

Q = lambda s: {"messages": [{"role": "user", "content": s}]}
ev = {}
WRITE = ("用 write_file 把 '三角对比实验数据' 写入 /workspace/tri.md，写完 read_file 确认。")
READ  = "用 read_file 读取 /workspace/tri.md，原样说出内容；若读不到就明说读不到。"

def brief(tag, r):
    txt = str(r["messages"][-1].content)
    print(f"[{tag}] {txt[:110]!r}")
    return txt

print("======== 角1 State（内存草稿本）========")
st = create_deep_agent(model=model)
st.invoke(Q(WRITE))
r = st.invoke(Q(READ))                       # 不带 files → 预期丢
ev["state_reread"] = brief("State 重读", r)

print("\n======== 角2 Filesystem（磁盘）========")
ROOT = "/root/ch03_hw/bonus_fs"; os.makedirs(ROOT, exist_ok=True)
fb = FilesystemBackend(root_dir=ROOT, virtual_mode=True)
create_deep_agent(model=model, backend=fb).invoke(Q(WRITE))
r = create_deep_agent(model=model,            # 全新实例
        backend=FilesystemBackend(root_dir=ROOT, virtual_mode=True)).invoke(Q(READ))
ev["fs_reread_new_instance"] = brief("FS 新实例读", r)   # 预期在

print("\n======== 角3 Store（键值库）========")
store = InMemoryStore()
NS = lambda rt: ("ch03hw", "files")          # namespace 工厂：所有文件进这一格
sb = StoreBackend(namespace=NS, store=store)
agent_s1 = create_deep_agent(model=model, backend=sb)
agent_s1.invoke(Q(WRITE))

# 3a) 全新 Agent 实例 + 同一个 store → 还在（跨实例）
agent_s2 = create_deep_agent(model=model,
                             backend=StoreBackend(namespace=NS, store=store))
r = agent_s2.invoke(Q(READ))
ev["store_new_instance_reread"] = brief("Store 新实例读", r)

# 3b) 直接看 store 内部（绕开 Agent 的证据）
items = [(i.key, i.value) for i in store.search(("ch03hw", "files"))]
ev["store_items"] = [{"key": k, "value_preview": str(v)[:120]} for k, v in items]
print("store.search 内部记录:", ev["store_items"])

# 3c) 换一个全新 store（等价于进程重启且没接持久库）→ 没了
store_fresh = InMemoryStore()
agent_s3 = create_deep_agent(model=model,
                             backend=StoreBackend(namespace=NS, store=store_fresh))
r = agent_s3.invoke(Q(READ))
ev["store_fresh_store_reread"] = brief("Store 换新库读", r)   # 预期丢

# ---------- 三角判定 ----------
def hit(t): return "三角对比实验数据" in t
verdict = {
    "state_lost_without_files":   not hit(ev["state_reread"]),
    "fs_survives_new_instance":   hit(ev["fs_reread_new_instance"]),
    "store_survives_new_instance":hit(ev["store_new_instance_reread"]),
    "store_dies_with_new_store":  not hit(ev["store_fresh_store_reread"]),
}
ev["verdict"] = verdict
json.dump(ev, open("hw_bonus_evidence.json", "w"), ensure_ascii=True, indent=1)
print("\n==== 三角判定 ====")
for k, v in verdict.items():
    print(f"  {k}: {v}")
print("[SAVED] hw_bonus_evidence.json")
print("DONE" if all(verdict.values()) else "CHECK_PARTIAL")

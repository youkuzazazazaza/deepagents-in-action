# 第3章作业·学有余力 教学详解：State / Filesystem / Store 三角对比

## 一、这一关到底在考什么

补上第三种后端 StoreBackend，做三角对照。StoreBackend 把文件放进 LangGraph 的 BaseStore（键值仓库）：按 namespace（命名空间）分格子，跨 invoke、跨 Agent 实例、跨 thread 都在；生命周期 = store 实例本身。

比喻：
- State = 草稿本（跟人走，交卷即焚）
- Filesystem = 真房子（跟磁盘走，人走家还在）
- Store = 仓库（跟仓库走，仓库在货就在；本实验用内存仓库，关仓即清；生产接 PostgresStore 就是永久仓库）

## 二、完整代码（注释齐全）

```python
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

```

## 三、逐段拆解（大白话）

**1. 接线：仓库和抽屉**
`InMemoryStore()` 造一个内存仓库；`namespace=lambda rt: ("ch03hw", "files")` 给每个 thread（rt）分同一个抽屉——注意 namespace 是元组，相当于多级抽屉路径。`StoreBackend(namespace=..., store=...)` 在构造时直接把仓库传进去，跟 FilesystemBackend 传 root_dir 一个套路，不需要 checkpointer。

**2. 三角同一条指令**
三个后端各自执行同一句话：写 `/workspace/tri.md`，再用最坏情况提问（新会话/新实例/新仓库）验货。

**3. 角 3 的三连问**
- 3a：同一个 store，new 一个全新 Agent 实例 → 照样读到。货在仓库，跟谁上门无关
- 3b：`store.search(("ch03hw", "files"))` 直接开仓盘点，能看到内部记录：key 是虚拟路径，value 里有内容（"写入内容"，有的后端还给 tuple 的 (content, timestamps) 结构）、namespace、创建/更新时间戳。文件在仓库里长什么样，肉眼可见
- 3c：new 一个全新的 store 实例（搬进一间刚清空的仓库）→ `path_not_found`。货的生死绑定在仓库实例上

## 四、跑起来长什么样（真实输出摘录）

`store.search` 开仓看到的记录（截选）：
```
[{"key": "/workspace/tri.md", "value_preview": "{'content': '三角对比实验数据\\n', 'encoding': 'utf-8', 'created_at': '2026-10-17T10:49:29.662211+00:00', 'modified_at': '2026-10"}]
```
四项判定：`state_dies_per_invoke=True, fs_survives_new_instance=True, store_survives_new_instance=True, store_dies_with_new_store=True`，全部命中预期。

## 五、这一关的坑

1. **namespace 用元组**：传字符串会被当成单级命名空间，跟分格设计对不上；多级用 `("a", "b")`
2. **换 store = 换仓库全丢**：InMemoryStore 重启进程即清零；要跨进程持久就接 LangGraph 的 PostgresStore
3. 本实验只验"在/不在"。Store 的看家本领 `search`（按 namespace 检索、配向量可语义召回）值得单独开实验

## 六、一句话记住 + 三角总表

| 后端 | 文件真实住处 | 生死跟谁走 | 一句话 |
|---|---|---|---|
| State | state["files"] | 一次 invoke | 草稿本，交卷即焚 |
| Filesystem | root_dir 磁盘 | 磁盘目录 | 真房子，人走家还在 |
| Store | BaseStore 命名空间 | store 实例 | 仓库，接 Postgres 跨进程 |

# ============================================================
# 【第3章 作业·Advanced 挑战级】State vs Filesystem：
#        生命周期对比 + 覆盖前后差异（全部留下可复现记录）
# ============================================================
# 实验设计（每个结论都有独立证据行）：
#   A) 生命周期：同一任务在两种 Backend 下各跑两轮（第二轮不带任何 state）
#      - StateBackend：第2轮文件消失 → 生命周期 = 一次 invoke
#      - FilesystemBackend：第2轮（甚至换一个全新 Agent 实例）文件仍在
#                          → 生命周期 = 磁盘上的文件
#   B) 覆盖差异：同一路径 write_file 两次（v1 → v2）
#      - 覆盖后 read_file 只看得到 v2
#      - StateBackend：v1 还活在"上一轮返回值的 files 快照"里，可整包救回
#      - FilesystemBackend：磁盘被就地覆盖，v1 彻底没了（除非你自己备份）
#   所有中间产物 dump 成 JSON，任何人重跑脚本可得到同样的判定逻辑。
#
# 跑法（WSL）：
#   cd /root/ch03_hw && /root/research_deepagent/.venv/bin/python \
#       /mnt/d/gitcode/learn/deepagents-in-action/task2_ch03/homework/code/hw_advanced.py
# ============================================================
import os, json, hashlib, subprocess

def load_env(p):
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env("/root/research_deepagent/.env")

from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
    max_retries=2,
)

ROOT = "/root/ch03_hw/adv_fs"
os.makedirs(ROOT, exist_ok=True)
V1 = "# 版本一\n初稿：三种后端都要对比\n"
V2 = "# 版本二\n终稿：聚焦 State 与 Filesystem 的生命周期差异\n"

def sha(t):
    return hashlib.sha256(t.encode()).hexdigest()[:12]

def brief(tag, r):
    txt = str(r["messages"][-1].content)
    print(f"[{tag}] 最终回答≈ {txt[:120]!r}")
    return txt

ev = {}          # 汇总证据（可复现记录）
Q = lambda s: {"messages": [{"role": "user", "content": s}]}

print("======== A) 生命周期对比 ========")
# ---- A1 StateBackend：默认后端 ----
st = create_deep_agent(model=model)          # 不传 backend = StateBackend
r = st.invoke(Q("用 write_file 把 '草稿A' 三个字写入 /workspace/life.md，写完 read_file 确认。"))
ev["state_round1_files"] = list((r.get("files") or {}).keys())
print("A1 State 第1轮 files =", ev["state_round1_files"])

r2 = st.invoke(Q("用 ls 列出 /workspace，并用 read_file 尝试读取 /workspace/life.md。如实报告结果。"))
ev["state_round2_files"] = list((r2.get("files") or {}).keys())
ev["state_round2_answer"] = brief("A2 State", r2)          # 预期：文件没了

# ---- A2 FilesystemBackend：换全新实例（比换 invoke 更狠） ----
fs1 = create_deep_agent(model=model,
                        backend=FilesystemBackend(root_dir=ROOT, virtual_mode=True))
r3 = fs1.invoke(Q("用 write_file 把 '草稿B' 三个字写入 /workspace/life.md，写完 read_file 确认。"))
ev["fs_round1_files"] = subprocess.run(["find", ROOT, "-type", "f"],
                                       capture_output=True, text=True).stdout.split()
print("A3 FS 第1轮 磁盘文件 =", ev["fs_round1_files"])

fs2 = create_deep_agent(model=model,           # ← 全新实例、全新进程内对象
                        backend=FilesystemBackend(root_dir=ROOT, virtual_mode=True))
r4 = fs2.invoke(Q("用 read_file 读取 /workspace/life.md，原样说出内容。"))
ev["fs_round2_answer"] = brief("A4 FS新实例", r4)           # 预期：还能读到

# ---- A3 Filesystem 的"死法"：删磁盘文件 ----
subprocess.run(["rm", "-rf", ROOT])
r5 = fs2.invoke(Q("再用 read_file 读取 /workspace/life.md，如实报告结果。"))
ev["fs_after_rm_answer"] = brief("A5 FS删盘后", r5)         # 预期：读不到了

print("\n======== B) 覆盖前后差异 ========")
# ---- B1 StateBackend：覆盖 + 快照救回 ----
st2 = create_deep_agent(model=model)
rv1 = st2.invoke(Q(f"用 write_file 把下面内容原样写入 /workspace/doc.md，写完 read_file 确认：\n{V1}"))
snap1 = rv1.get("files") or {}                              # ← v1 的"孤儿快照"
rv2 = st2.invoke({"messages": [{"role": "user", "content":
        f"用 read_file 读 /workspace/doc.md（若无文件，正常，忽略），然后无论如何用 write_file "
        f"把下面内容覆盖写入 /workspace/doc.md，写完 read_file 确认：\n{V2}"}],
        "files": snap1})                                    # 带上 v1 快照，模拟连续工作
snap2 = rv2.get("files") or {}
ev["state_v1_hash"] = sha(str(snap1.get("/workspace/doc.md", "")))
ev["state_v2_hash"] = sha(str(snap2.get("/workspace/doc.md", "")))
print("B1 State 覆盖：v1 快照哈希", ev["state_v1_hash"], " v2 哈希", ev["state_v2_hash"])
rrescue = st2.invoke({"messages": [{"role": "user", "content":
    "用 read_file 读取 /workspace/doc.md，原样说出内容。"}], "files": snap1})
ev["state_rescue_answer"] = brief("B1 State救回(喂v1快照)", rrescue)  # 预期：回到版本一

# ---- B2 FilesystemBackend：就地覆盖，v1 无处可寻 ----
os.makedirs(ROOT, exist_ok=True)
fsw = create_deep_agent(model=model,
                        backend=FilesystemBackend(root_dir=ROOT, virtual_mode=True))
fsw.invoke(Q(f"用 write_file 把下面内容原样写入 /workspace/doc.md：\n{V1}"))
disk_v1 = open(os.path.join(ROOT, "workspace", "doc.md"), encoding="utf-8").read()
fsw.invoke(Q(f"用 write_file 把下面内容覆盖写入 /workspace/doc.md，写完 read_file 确认：\n{V2}"))
disk_v2 = open(os.path.join(ROOT, "workspace", "doc.md"), encoding="utf-8").read()
ev["fs_v1_hash"] = sha(disk_v1); ev["fs_v2_hash"] = sha(disk_v2)
ev["fs_v1_recoverable"] = False   # 磁盘已被就地覆盖，v1 无来源可读
print("B2 FS 覆盖：磁盘 v1", ev["fs_v1_hash"], "→ v2", ev["fs_v2_hash"],
      "(v1 已被就地覆盖)")

# ---------- 判定（可复现：重跑脚本即重算这四行） ----------
verdict = {
    "state_round2_lost":  len(ev["state_round2_files"]) == 0 and "life.md" in str(ev.get("state_round2_answer", "")),
    "fs_new_instance_ok": "草稿B" in ev["fs_round2_answer"],
    "fs_dies_with_disk":  "草稿B" not in ev["fs_after_rm_answer"],
    "state_snapshot_rescue": "版本一" in ev["state_rescue_answer"],
    "fs_overwrite_destroys_v1": (ev["fs_v1_hash"] != ev["fs_v2_hash"]),
}
ev["verdict"] = verdict
json.dump(ev, open("hw_advanced_evidence.json", "w"), ensure_ascii=True, indent=1)
print("\n==== 判定 ====")
for k, v in verdict.items():
    print(f"  {k}: {v}")
print("[SAVED] hw_advanced_evidence.json")
print("DONE" if all(verdict.values()) else "CHECK_PARTIAL")

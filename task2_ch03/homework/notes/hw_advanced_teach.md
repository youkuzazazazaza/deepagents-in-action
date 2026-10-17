# 第3章作业·Advanced 挑战级 教学详解：生命周期 + 覆盖差异，五项判定全留证

## 一、这一关到底在考什么

两个问题：① 同一个文件，在 StateBackend 和 FilesystemBackend 下各能活多久？② `write_file` 覆盖同名文件时，旧版本是死是活？

比喻先行：
- StateBackend 像草稿本，Agent 交卷（invoke 结束）就把纸撕了，但撕之前抄给你的那份（返回值里的 `files`）还在你手里
- FilesystemBackend 像一间真房子，Agent 走了东西还在，除非你把房子拆了（删磁盘目录）

## 二、完整代码（注释齐全）

```python
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

```

## 三、逐段拆解（大白话）

**A 组：生命周期对照实验**
- A1 用 StateBackend（`create_deep_agent` 不传 backend 时的默认值）第 1 轮写入 `/workspace/life.md`，返回值 `r["files"]` 里能看到它
- A2 同一个 Agent 再 invoke 一次，让它 `ls /workspace` 并尝试读取。结果目录空的：第 2 轮的 state 里没人给它带 `files`，草稿纸随上一轮交卷撕掉了
- A3 换 FilesystemBackend，第 1 轮写入后用 `find` 列磁盘真相
- A4 更狠的一步：new 一个全新 Agent 实例 `fs2`，直接把"住进房子的人"整个换掉（比换一次 invoke 更彻底），它照样读回"草稿B"。因为读的是房子里的东西，跟谁住进来无关
- A5 FilesystemBackend 的死法：`rm -rf ROOT` 拆房子，`fs2` 立刻失明。它死于磁盘，不死于会话

**B 组：覆盖前后差异**
- B1 StateBackend：第 1 轮写入 v1 后，返回值 `snap1` 就是 v1 的孤儿快照（那轮对话已结束，state 本体没了，快照在我手里）。第 2 轮我手动把 `snap1` 塞进 invoke 输入的 `files` 字段（喂回记忆），再让它覆盖成 v2。之后单独发起第 3 轮，仍然喂 `snap1`：Agent 读回"版本一"。旧版本躺在快照里，可整包救回，这就是后悔药
- B2 FilesystemBackend：同样 v1→v2 覆盖，我两次直读磁盘算 sha256（前 12 位 `938c10bcbaf8` → `d5e92dd2d5ea`）。hash 变了证明确实覆盖；磁盘上 v1 已被就地销毁，任何地方都读不回来。除非你自己先备份，没有后悔药

**判定逻辑逐行讲**
- `state_round2_lost`：第 2 轮 files 为空 且 Agent 回答里提到 life.md（空目录 + 它试图找过，说明文件真没了，指令没被曲解）
- `fs_new_instance_ok`：全新实例回答里含"草稿B"（跨实例可读）
- `fs_dies_with_disk`：删盘后回答里不含"草稿B"（死于磁盘）
- `state_snapshot_rescue`：喂回 snap1 后读出"版本一"（快照可救）
- `fs_overwrite_destroys_v1`：磁盘 v1/v2 hash 不同（旧版就地蒸发）

## 四、跑起来长什么样（真实输出摘录）

```
A1 State 第1轮 files = ['/workspace/life.md']
A2 State 第2轮 files = []（第2轮回答：目录为空，文件不存在）
A4 FS新实例 读回：草稿B
A5 FS删盘后：文件不存在
B1 State 覆盖：v1 快照哈希 46ec342199ba  v2 哈希 eed742aba06b
B2 FS 覆盖：磁盘 v1 938c10bcbaf8 → v2 d5e92dd2d5ea（v1 已被就地覆盖）
==== 判定 ==== 五项全部 True
```

## 五、这一关的坑

1. **State 的正确接棒姿势**：想让 State 后端跨轮连续工作，必须手动把上一轮返回值的 `files` 塞进下一轮 invoke 输入，框架不会替你带
2. **取证别用嘴**：覆盖前后的差异用 sha256 留档，重跑脚本 hash 可复算；口头说"内容变了"没有证据力
3. 老朋友再出现：B2 直读磁盘的路径是 `ROOT/workspace/doc.md`，`/workspace` 段照旧保留

## 六、一句话记住

State 跟人走（一次 invoke），FS 跟房走（磁盘目录）；覆盖时 State 留底片，FS 烧底片。

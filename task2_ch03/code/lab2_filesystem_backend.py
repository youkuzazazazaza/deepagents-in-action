# ============================================================
# 【第3章 Lab2】FilesystemBackend + CompositeBackend：真·落盘
# ============================================================
# 一句话：把虚拟文件系统挂到真实磁盘目录上，文件真的写进硬盘，
#         换一个 Agent 实例（甚至换一个进程）都还能读。
#
# 三个看点：
#   A) Agent A 写 → 磁盘上真的有这个文件（subprocess ls 验证）
#   B) Agent B（另一个实例）直接读到了 A 写的文件 → 跨实例持久化
#   C) CompositeBackend：/shared/** 落盘，其它路径留在内存 → 分区挂载
#
# 跑法（WSL）：
#   cd /root/ch03_labs && /root/research_deepagent/.venv/bin/python \
#       /mnt/d/gitcode/learn/deepagents-in-action/task2_ch03/code/lab2_filesystem_backend.py
# ============================================================
import os, json, subprocess

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
from deepagents.backends import FilesystemBackend, CompositeBackend, StateBackend

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
    max_retries=2,
)

ROOT = "/root/ch03_labs/fsroot"      # 真实磁盘目录（虚拟 /workspace 的家）
SHARED = "/root/ch03_labs/shared"    # Composite 的 /shared 挂载点
os.makedirs(ROOT, exist_ok=True)
os.makedirs(SHARED, exist_ok=True)

# ---------- A) 纯 FilesystemBackend：整个 VFS 都落盘 ----------
agent_a = create_deep_agent(
    model=model,
    backend=FilesystemBackend(root_dir=ROOT, virtual_mode=True),
    # virtual_mode=True：Agent 眼里还是 /workspace/xxx 的虚拟路径，
    #                    后端自动把它映射到 ROOT 下的真实文件
)
q = ("用 write_file 把 '# 第3章实验\n文件真的落盘了吗？' 写入 /workspace/report.md，"
     "然后 read_file 读回来确认。")
ra = agent_a.invoke({"messages": [{"role": "user", "content": q}]})
print("==== A) Agent A（FilesystemBackend）====")
for m in ra["messages"]:
    print(f"- {m.type:10s} {m.name or '':12s} {str(m.content)[:80]!r}")

# 磁盘验证：绕过 Agent，直接用 shell 看！（证据 > 一切）
out = subprocess.run(["ls", "-la", ROOT], capture_output=True, text=True).stdout
print("---- 磁盘真相（ls -la", ROOT, "）----")
print(out)

# ---------- B) 另一个实例 Agent B：跨实例读取 ----------
agent_b = create_deep_agent(
    model=model,
    backend=FilesystemBackend(root_dir=ROOT, virtual_mode=True),
)
rb = agent_b.invoke({"messages": [{"role": "user", "content":
    "用 read_file 读取 /workspace/report.md，原样说出全部内容。"}]})
print("\n==== B) Agent B（另一个实例）====")
final_b = rb["messages"][-1].content
print("B 的最终回答:", str(final_b)[:200])

# ---------- C) CompositeBackend：按路径"分区挂载" ----------
agent_c = create_deep_agent(
    model=model,
    backend=CompositeBackend(
        default=StateBackend(),   # 没匹配到的路径 → 内存（重启就没）
        routes={"/shared": FilesystemBackend(root_dir=SHARED, virtual_mode=True)},
        # routes 就像 /etc/fstab：/shared 这块"分区"挂到磁盘
        # ⚠️ 实测大坑：routes 的 key 是【纯路径前缀】，不是 glob！
        #   写 "/shared/**" 看起来很直觉，但它永远匹配不上 "/shared/notes.md"，
        #   文件会【静默】落进 default（内存）——磁盘上啥都没有，还不报错！
        #   （本 lab 第一版就踩了这坑，probe5b/probe6 双重实验证实）
    ),
)
qc = ("依次执行两次 write_file：1) 把 '团队共享笔记' 写入 /shared/notes.md；"
      "2) 把 '我的私人草稿' 写入 /workspace/draft.md。")
rc = agent_c.invoke({"messages": [{"role": "user", "content": qc}]})
print("\n==== C) CompositeBackend 分区验证 ====")
print("Agent C 的 files:", list((rc.get("files") or {}).keys()))
print("---- 磁盘真相 shared/ ----")
print(subprocess.run(["ls", "-la", SHARED], capture_output=True, text=True).stdout)
print("预期：/shared/notes.md 在磁盘；/workspace/draft.md 只在内存（default=StateBackend）")

# ---------- 存证据 ----------
json.dump({
    "disk_root": subprocess.run(["find", ROOT, "-type", "f"],
        capture_output=True, text=True).stdout.split(),
    "disk_shared": subprocess.run(["find", SHARED, "-type", "f"],
        capture_output=True, text=True).stdout.split(),
    "agentB_final": str(final_b)[:500],
}, open("lab2_evidence.json", "w"), ensure_ascii=True, indent=1)
print("[SAVED] lab2_evidence.json")
print("DONE" if "落盘" in str(final_b) else "CHECK_B")

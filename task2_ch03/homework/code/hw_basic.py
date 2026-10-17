# ============================================================
# 【第3章 作业·Basic 基础级】文件后端：保存、读回、修改"资料与报告"
# ============================================================
# 核心考点：讲清【文件路径】和【Backend】之间的关系。
#   - Agent 永远只看到虚拟路径 /workspace/资料/xxx.md（平台无关）
#   - FilesystemBackend 决定这些虚拟路径"翻译"到磁盘的哪个真实目录
#   - 换一个 root_dir，同一批虚拟路径就指向另一块磁盘——路径不变，家在变
#
# 跑法（WSL）：
#   cd /root/ch03_hw && /root/research_deepagent/.venv/bin/python \
#       /mnt/d/gitcode/learn/deepagents-in-action/task2_ch03/homework/code/hw_basic.py
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
from deepagents.backends import FilesystemBackend

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
    max_retries=2,
)

# 同一批"虚拟路径"，两个不同的家：
ROOT_A = "/root/ch03_hw/basic_a"     # Backend A 的家
ROOT_B = "/root/ch03_hw/basic_b"     # Backend B 的家（故意不同，证明路径与家无关）
for d in (ROOT_A, ROOT_B):
    os.makedirs(d, exist_ok=True)

def make_agent(root):
    return create_deep_agent(
        model=model,
        backend=FilesystemBackend(root_dir=root, virtual_mode=True),
    )

def show(title, result):
    print(f"\n==== {title} ====")
    for m in result["messages"]:
        print(f"- {m.type:10s} {(m.name or ''):12s} {str(m.content)[:90]!r}")

agent_a = make_agent(ROOT_A)

# ---------- 第 1 步：保存"资料" ----------
q1 = ("用 write_file 把下面资料原样写入 /workspace/资料/research.md：\n"
      "# 调研要点\n"
      "1. StateBackend 只活在一次 invoke 里\n"
      "2. FilesystemBackend 真落盘，跨实例可读\n"
      "3. 上下文超长会自动截断，这条已过时待订正\n")
r1 = agent_a.invoke({"messages": [{"role": "user", "content": q1}]})
show("第1步 保存资料 research.md（第3条故意过时）", r1)

# ---------- 第 2 步：读回 ----------
r2 = agent_a.invoke({"messages": [{"role": "user", "content":
    "用 read_file 读取 /workspace/资料/research.md，原样复述内容。"}]})
show("第2步 读回资料", r2)

# ---------- 第 3 步：修改资料（订正第3条） + 生成报告 ----------
q3 = ("先 read_file /workspace/资料/research.md；然后："
      "1) 把第 3 条整行替换为 3. 大结果会自动卸载到文件，对话历史会自动总结；"
      "用 write_file 覆盖写回同一路径；"
      "2) 再用 write_file 新建 /workspace/报告/report.md，内容是三行，"
      "每行以 结论N: 开头，把三条要点各浓缩成一句话。")
r3 = agent_a.invoke({"messages": [{"role": "user", "content": q3}]})
show("第3步 修改资料 + 生成报告", r3)

# ---------- 第 4 步：磁盘真相 + 路径与 Backend 关系证明 ----------
disk = subprocess.run(["find", ROOT_A, "-type", "f"], capture_output=True, text=True).stdout
print("==== 磁盘真相（find", ROOT_A, "）====")
print(disk)
fixed = open(os.path.join(ROOT_A, "workspace/资料/research.md"), encoding="utf-8").read()
report = open(os.path.join(ROOT_A, "workspace/报告/report.md"), encoding="utf-8").read()
print("---- research.md（订正后）----"); print(fixed)
print("---- report.md ----"); print(report)

# 关键对照：同样的虚拟路径，挂到另一个 Backend（ROOT_B）→ 那边什么都没有！
agent_b = make_agent(ROOT_B)
r4 = agent_b.invoke({"messages": [{"role": "user", "content":
    "用 ls 列出 /workspace 下所有内容（包括子目录），用 read_file 尝试读 /workspace/资料/research.md，"
    "如实报告看到了什么。"}]})
show("第4步 同样路径挂到另一个家 ROOT_B → 找不到", r4)

ok = ("自动卸载" in fixed) and report.count("结论") >= 3
json.dump({
    "disk_a_files": disk.split(),
    "research_md_fixed": fixed,
    "report_md": report,
    "b_final": str(r4["messages"][-1].content)[:300],
    "check": {"fixed_and_report": ok},
}, open("hw_basic_evidence.json", "w"), ensure_ascii=True, indent=1)
print("[SAVED] hw_basic_evidence.json")
print("DONE" if ok else "CHECK")

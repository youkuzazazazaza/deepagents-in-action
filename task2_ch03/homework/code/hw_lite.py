# ============================================================
# 【第3章 作业·Lite 打卡级】写入 — 读回 — 修改，产物真在项目目录
# ============================================================
# 打卡要求里最容易被忽略的一条：不是 Agent 说"我写好了"就算数，
# 要【绕开 Agent、亲手在项目目录里找到那份产物】。
# 所以本脚本最后一步用 subprocess 直接 cat 磁盘文件 —— 证据 > 一切。
#
# 跑法（WSL）：
#   mkdir -p /root/ch03_hw && cd /root/ch03_hw && /root/research_deepagent/.venv/bin/python \
#       /mnt/d/gitcode/learn/deepagents-in-action/task2_ch03/homework/code/hw_lite.py
# ============================================================
import os, json, subprocess

# ---------- 第 0 步：加载 .env（Key 绝不明文写） ----------
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

ROOT = "/root/ch03_hw/lite_proj"          # ← "项目目录"，虚拟 /workspace 的家
os.makedirs(ROOT, exist_ok=True)

agent = create_deep_agent(
    model=model,
    backend=FilesystemBackend(root_dir=ROOT, virtual_mode=True),
    # virtual_mode=True：Agent 眼中始终是 /workspace/xxx（虚拟路径），
    #                    后端悄悄把它翻译成 ROOT 下的真实文件。
)

def show(title, result):
    print(f"\n==== {title} ====")
    for m in result["messages"]:
        head = str(m.content)[:100].replace("\n", " ")
        print(f"- {m.type:10s} {(m.name or ''):12s} {head!r}")

# ---------- 第 1 步：写入（故意留一个错日期，给第 3 步"修改"用） ----------
q1 = ("请用 write_file 把下面内容原样写入 /workspace/meeting.md：\n"
      "# 周会纪要\n"
      "- 下次例会时间 2026-10-11 上午十点\n"
      "- 负责人 小王\n"
      "写完后用 read_file 读回来确认。")
r1 = agent.invoke({"messages": [{"role": "user", "content": q1}]})
show("第1步 写入 meeting.md（含错日期 10-11）", r1)

# ---------- 第 2 步：读回（单独一轮，只靠磁盘，不带任何 state） ----------
q2 = "用 read_file 读取 /workspace/meeting.md，把内容原样告诉我。"
r2 = agent.invoke({"messages": [{"role": "user", "content": q2}]})
show("第2步 读回（新 invoke，文件仍在 = 已落盘）", r2)

# ---------- 第 3 步：修改（覆盖式 write_file 修正日期 + 追加一行） ----------
q3 = ("用 read_file 读取 /workspace/meeting.md，然后做两处修改后用 write_file 覆盖写回同一路径："
      "1) 把例会时间从 2026-10-11 改成 2026-10-18；"
      "2) 在文件末尾追加一行 - 纪要归档 会议纪要目录。"
      "改完再 read_file 确认。")
r3 = agent.invoke({"messages": [{"role": "user", "content": q3}]})
show("第3步 修改（改日期 + 追加一行）", r3)

# ---------- 第 4 步：亲手在项目目录找产物（绕开 Agent 的磁盘真相） ----------
# 坑点：virtual_mode=True 时 /workspace/xxx 落盘在 ROOT/workspace/xxx
#       （虚拟路径的"挂载点名"也被原样保留），别去 ROOT/xxx 下找！
disk_ls = subprocess.run(["find", ROOT, "-type", "f"], capture_output=True, text=True).stdout
disk_cat = open(os.path.join(ROOT, "workspace", "meeting.md"), encoding="utf-8").read()
print("==== 项目目录真相（find", ROOT, "）====")
print(disk_ls)
print("---- meeting.md 磁盘原文 ----")
print(disk_cat)

# ---------- 存证据 ----------
ok_fixed = "2026-10-18" in disk_cat and "2026-10-11" not in disk_cat
ok_append = "会议纪要目录" in disk_cat
json.dump({
    "disk_ls": disk_ls,
    "disk_meeting_md": disk_cat,
    "r2_final": str(r2["messages"][-1].content)[:300],
    "r3_final": str(r3["messages"][-1].content)[:300],
    "check": {"date_fixed": ok_fixed, "line_appended": ok_append},
}, open("hw_lite_evidence.json", "w"), ensure_ascii=True, indent=1)
print("[SAVED] hw_lite_evidence.json")
print("DONE" if (ok_fixed and ok_append) else "CHECK")

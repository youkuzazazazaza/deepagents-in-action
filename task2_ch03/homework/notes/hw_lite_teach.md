# 第3章作业·Lite 打卡级 教学详解：写入 — 读回 — 修改

## 一、这一关到底在考什么

一句话：让 Agent 完成"写文件、读文件、改文件"三步，最后你要绕开 Agent，自己去磁盘上把文件找出来。

Agent 嘴上说"我写好了"不算数。它可能真写了，也可能幻觉了。判定标准只有一条：磁盘上那份文件里，日期改对了、新行加上了。所以脚本最后一步完全不用 Agent 的任何工具，直接用 `find` 和 `open()` 亲手验货。

比喻：Agent 像替你跑腿的实习生，实习生说"文件放柜子了"，你要自己走过去开柜门看一眼。

## 二、完整代码（注释齐全）

```python
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

```

## 三、逐段拆解（大白话）

**1. load_env：自己动手读 .env**
密钥不能明文写进代码（会跟着 git 泄露），所以放在 `.env` 文件里，脚本启动时读进环境变量。`os.environ.setdefault` 的意思是：如果环境里已经有这个变量，就不覆盖，尊重现成的。

**2. ChatOpenAI 三件套**
`model` 是用哪个模型，`api_key` 是钥匙，`base_url` 是服务地址。`max_retries=2` 让网络抖一下时自动重试两次，脚本不至于一抖就崩。

**3. FilesystemBackend(root_dir=ROOT, virtual_mode=True)：本关主角**
- `root_dir` 是"家"：Agent 写的所有文件，真实落盘都在这个目录里
- `virtual_mode=True` 是"虚拟路径"：Agent 眼中永远只看到 `/workspace/meeting.md` 这种统一门牌，后端悄悄把它翻译成 `ROOT` 下的真实文件
- 好处：提示词、工具说明里写死 `/workspace` 就行，不用管跑在谁的电脑上、家安在哪

**4. 三轮 invoke = 三次全新对话**
`agent.invoke()` 每次都是独立会话，上一轮聊了什么 Agent 全忘。第 2 轮还能读到文件，说明文件真的存在后端里，跟"聊天记忆"无关。第 1 轮我故意埋了个错日期（当天实际是 10-17，纪要里写 10-11），让第 3 轮的"修改"有真事可干，验证才有分辨力：改对了能查出来，改错了也瞒不过判定。

**5. 第 4 步：亲手验货**
`find ROOT -type f` 列出磁盘上真实存在的文件；`open()` 直读文件原文。这两步都不经过 Agent，Agent 编不了。

**6. 自动判定**
`ok_fixed` 要求新日期在、旧日期不在（半改不算过）；`ok_append` 检查新加的那一行。结果存进 `hw_lite_evidence.json`，重跑可复查。

## 四、跑起来长什么样（真实输出摘录）

第 2 轮读回时，Agent 原样报出了含错日期的内容（写读无污染）：
```
以下是 `/workspace/meeting.md` 的完整内容：

```
# 周会纪要
- 下次例会时间 2026-10-11 上午十点
- 负责人 小王
```

文件共 3 行，没有其他内容。
```
跑完第 3 轮后，磁盘上的最终原文（日期已改、新行已加）：
```
# 周会纪要
- 下次例会时间 2026-10-18 上午十点
- 负责人 小王
- 纪要归档 会议纪要目录

```
判定结果：`date_fixed=True, line_appended=True`，文件真实路径 `/root/ch03_hw/lite_proj/workspace/meeting.md`。

## 五、这一关的坑

1. **落盘位置坑**：`virtual_mode=True` 时 `/workspace/meeting.md` 实际落在 `ROOT/workspace/meeting.md`。虚拟路径开头的 `/workspace` 这一段会被原样保留在目录结构里，直接去 `ROOT/meeting.md` 找必然 FileNotFoundError。
2. **信任坑**：只看 Agent 回复就宣布成功，等于没验证。判定交给代码，不交给嘴。

## 六、一句话记住

文件真假不看嘴，`find` 加 `open` 说了算。

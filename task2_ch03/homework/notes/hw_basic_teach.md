# 第3章作业·Basic 基础级 教学详解：路径是门牌，Backend 是小区

## 一、这一关到底在考什么

讲清"文件路径"和"Backend"的关系。Agent 永远只看虚拟路径（如 `/workspace/资料/research.md`），但这条路径真实落在哪块磁盘，由 Backend 的 `root_dir` 说了算。

比喻：`/workspace/资料/research.md` 是门牌号，`root_dir` 是小区。门牌号一模一样，小区不同就是两套房。Agent A 住在 `basic_a` 小区，Agent B 住在 `basic_b` 小区；A 家里放的文件，B 按同样门牌去敲，敲开门也是空的。

## 二、完整代码（注释齐全）

```python
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

```

## 三、逐段拆解（大白话）

**1. 两个家，一个工厂**
`make_agent(root)` 是个小工厂：同一个模型，传不同的 `root_dir` 就造出住在不同小区的 Agent。`ROOT_A` 给 A，`ROOT_B` 给 B，故意不同，这正是实验变量。

**2. A 的三轮：写、读、改+生成**
- 第 1 轮写资料，第 3 条我故意写成过时的"上下文超长会自动截断"
- 第 2 轮读回，确认写读链路干净
- 第 3 轮一口气干两件事：先订正第 3 条（整行替换成正确说法），再新建报告文件、把三条要点各浓缩成一行。这一轮考的是 Agent 连续调用工具的能力：读、改、再写，一个会话里串起来

**3. B 的对照：同样的门牌，另一家小区**
B 拿到的指令和 A 看到的路径完全一样，但 B 的家在 `ROOT_B`。结果它 `ls /workspace` 报 `path_not_found`，`read_file` 报文件不存在，连 `/tmp`、`/home` 都试了一遍，最后如实承认读不到。注意两点：它没有幻觉编造内容；错误信息来自工具层，足够诚实。这说明虚拟路径相同不代表看到同一批文件。

**4. 磁盘验货**
`find ROOT_A` 列出 A 家的真实文件；两个 `open()` 分别直读订正后的资料和报告原文，绕开 Agent。判定 `ok` 要求资料里出现"自动卸载"（订正生效）且报告至少三行带"结论"。

## 四、跑起来长什么样（真实输出摘录）

A 家磁盘上的文件清单（注意都在 `basic_a/workspace/` 下）：
```
/root/ch03_hw/basic_a/workspace/报告/report.md
/root/ch03_hw/basic_a/workspace/资料/research.md
```
B 的最终自述（如实报错，不编内容）：
```
## 如实报告

**任务未能完成：`/workspace` 在文件系统中不存在，你提到的文件也读不到。**

以下是我实际执行的调用和得到的原始结果：

| 调用 | 目标 | 结果 |
|---|---|---|
| `ls` | `/workspace` | ❌ `Error: Path '/workspace': path_not_found` |
| `read_file` | `/workspace/资料/research.
```
判定结果：`fixed_and_report=True`。

## 五、这一关的坑

1. **换 root_dir = 换家**：想让两个 Agent 共享文件，就让它们用同一个 `root_dir`；想隔离，就分家。路径写得再一样也没用，家决定一切。
2. **验货路径同样要加 `workspace` 段**：磁盘直读要拼 `ROOT_A/workspace/资料/research.md`，跟 Lite 关是同一个坑。

## 六、一句话记住

路径是门牌，`root_dir` 是小区；门牌一样、小区不同，互相就是看不见。

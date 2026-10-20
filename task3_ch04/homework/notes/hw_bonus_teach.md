# 第4章作业·学有余力 教学详解：Summarization × Todo，压缩后清单还活着吗

## 一、这一关到底在考什么

一句话：把对话拉长、把摘要阈值调低（trigger 10 条、keep 4 条），让**上下文压缩真实发生**，然后检查四件事：① state 里的消息真的变少了吗（压缩改的是状态还是只改请求）；② todos 字段会不会跟着消息一起被"压没"；③ 最早的细节（A001=299）压缩后还记得吗；④ 磁盘上会不会多出归档文件。

第 4 章开头那句"复杂任务做着做着就忘了自己在干嘛"，本章给了两味药：**TodoListMiddleware**（把计划写进独立 state 字段）和 **SummarizationMiddleware**（消息超阈值就摘要压缩）。Bonus 的实验设计就是把两味药同时喂给同一个 Agent，再用五轮对话追问细节，专门盯着"压缩的牙齿"看它咬掉了什么、留下了什么。

比喻：消息历史是仓库里的原始单据，摘要压缩是定期把旧单据碎掉、只留一张手写台账；todos 和磁盘文件是刻在石头上的账本。碎纸机开动后，单据没了，但石头上的字一个都没少——旧细节只要进了台账（摘要）或刻上了石头（todos/文件），就还查得到。

三个值得先记住的观察点：
- **消息数的锯齿**：不压缩应一路上涨（6→10→12→14→16）；真被压缩会掉下来（本实验实测 6→10→8→6→8）。
- **压缩改的是 state 本身**：`get_state()` 拿到的消息条数真的变少（不是"发给模型时临时码掉"）；且实测首条始终是 `HumanMessage`——摘要器保留最初的用户消息，替换的是中段历史。
- **T5 的记忆考验**：五轮后突然问第一轮的数字，答得出说明旧事实成功转进了摘要。

## 二、完整代码（注释齐全）

```python
# ============================================================
# 【第4章 作业·Bonus 附加题】Summarization × Todo：
#           上下文被压缩后，任务清单还活着吗？
# ============================================================
# 实验设计（对照第 4 章"长任务忘事"的两大解药）：
#   1. TodoListMiddleware   —— 把计划写进独立 state 字段 todos
#   2. SummarizationMiddleware —— 消息超过 trigger 就摘要压缩
# 核心问题：消息历史被压缩后——
#   - state 里的消息还剩几条？（压缩是改 state 还是只改请求？）
#   - todos 字段还在吗？（清单会不会跟着消息一起被"压没"）
#   - 还记得最早的细节吗？（A001 金额 / 满减门槛）
#   - 磁盘上会不会出现归档文件？
#
# 跑法（WSL）：
#   cd /root/ch04_hw && /root/research_deepagent/.venv/bin/python \
#       /mnt/d/gitcode/learn/deepagents-in-action/task3_ch04/homework/code/hw_bonus.py
# ============================================================
import os, json, shutil

def load_env(p):
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env("/root/research_deepagent/.env")

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
    max_retries=2,
    temperature=0,
)

# ---------- 工作区：老三样（和 basic/advanced 同一套数据，答案已知） ----------
ROOT = "/root/ch04_hw/bonus"
ORDERS = "\n".join([
    "A001,无线鼠标,299.00", "A002,机械键盘,159.50",
    "A003,显示器支架,140.00", "A003,显示器支架,140.00",   # 重复行（雷）
    "A004,鼠标垫,60.00", "A005,USB-C 扩展坞,139.50",
]) + "\n"
PROMO = "全场满 400 减 30。\n"
SHIPPING = "应付金额满 99 元免运费，否则运费 10 元。\n"
GT = {"total": 798.00, "payable": 768.00, "shipping": 0.00}

def seed():
    shutil.rmtree(ROOT, ignore_errors=True)
    os.makedirs(ROOT, exist_ok=True)
    open(f"{ROOT}/orders.txt", "w", encoding="utf-8").write(ORDERS)
    open(f"{ROOT}/promo.txt", "w", encoding="utf-8").write(PROMO)
    open(f"{ROOT}/shipping.txt", "w", encoding="utf-8").write(SHIPPING)

def make_tools(root):
    """闭包工具：Agent 只能通过这三个工具看/写文件。"""
    from langchain_core.tools import tool

    @tool
    def ls() -> str:
        """列出 /workspace 下所有文件名（逗号分隔）。"""
        return ", ".join(sorted(os.listdir(root)))

    @tool
    def read_file(file_name: str) -> str:
        """读取 /workspace 下指定文件的全部内容。file_name 只填文件名。"""
        p = os.path.join(root, file_name)
        if not os.path.isfile(p):
            return f"错误：没有 {file_name}"
        return open(p, encoding="utf-8").read()

    @tool
    def write_file(file_name: str, content: str) -> str:
        """把 content 整体写入 /workspace 下的 file_name（覆盖式）。"""
        open(os.path.join(root, file_name), "w", encoding="utf-8").write(content)
        return f"已写入 {file_name}（{len(content)} 字符）"

    return [ls, read_file, write_file]

seed()

# ---------- 中间件组合：Todo(规划) + Summarization(压缩) ----------
# trigger=("messages", 10)：历史超过 10 条消息就触发摘要
# keep=("messages", 4)：   摘要后只保留最近 4 条消息
# —— 故意调小，让"压缩"在 5 轮对话里必然发生，肉眼可见。
agent = create_agent(
    model=model,
    tools=make_tools(ROOT),
    middleware=[
        TodoListMiddleware(),
        SummarizationMiddleware(model=model,
                                trigger=("messages", 10), keep=("messages", 4)),
    ],
    checkpointer=InMemorySaver(),   # 多轮记忆：同一 thread_id 连续对话
)
cfg = {"configurable": {"thread_id": "bonus-thread"}}

def snapshot(tag):
    """拍一张快照：state 消息数 / todos / 工作区文件。"""
    st = agent.get_state(cfg)
    msgs = st.values.get("messages", [])
    todos = st.values.get("todos", [])
    files = sorted(os.listdir(ROOT))
    first = type(msgs[0]).__name__ if msgs else "-"
    print(f"  [state] 消息 {len(msgs)} 条（首条类型 {first}）| "
          f"todos {len(todos)} 项 | 文件: {files}")
    return {"n_msgs": len(msgs), "n_todos": len(todos),
            "todos": todos, "files": files, "first": first}

def say(text):
    print(f"\n>> {text}")
    r = agent.invoke({"messages": [{"role": "user", "content": text}]}, cfg)
    ans = r["messages"][-1].content
    print(f"   Agent: {ans[:120]}{'...' if len(ans) > 120 else ''}")
    return ans

print("=" * 60)
print("Bonus：Summarization × Todo 五轮连续对话")
print("=" * 60)
snap0 = snapshot("开局")

# T1 重活：读三个文件 → 去重 → 写 report.md（会触发 write_todos 的典型场景）
a1 = say("请核对订单并写 report.md：先读 orders.txt/promo.txt/shipping.txt，"
         "注意订单号重复的行只算一次；算出 总额/应付金额/运费 写入 report.md，"
         "格式：总额=X 应付金额=Y 运费=Z。开始前先列个计划。")
snap1 = snapshot("T1 后")

# T2~T5 追问：每轮都要"回忆"或重读早期细节，把消息数推过 trigger
a2 = say("A005 买了什么？金额多少？")
snap2 = snapshot("T2 后")
a3 = say("满减门槛是多少？把 promo.txt 原文念给我听。")
snap3 = snapshot("T3 后")
a4 = say("运费规则的原文是什么？")
snap4 = snapshot("T4 后")
a5 = say("最后再报一次：A001 的金额是多少？总额是多少？")   # 压缩后的记忆考验
snap5 = snapshot("T5 后")

# ---------- 裁判 ----------
import re
rep = open(f"{ROOT}/report.md", encoding="utf-8").read() if \
    os.path.exists(f"{ROOT}/report.md") else ""
g = lambda p: (float(m.group(1)) if (m := re.search(p, rep)) else None)
got = (g(r"总额[=＝:\s]*(\d+(?:\.\d+)?)"),
       g(r"应付金额[=＝:\s]*(\d+(?:\.\d+)?)"),
       g(r"运费[=＝:\s]*(\d+(?:\.\d+)?)"))
report_ok = got == (GT["total"], GT["payable"], GT["shipping"])

a5_has_299 = "299" in a5

print("\n" + "=" * 60)
print("裁判结果")
print("=" * 60)
print(f"  report.md 三数字正确      : {report_ok}  (got={got})")
print(f"  T5 还记得 A001=299        : {a5_has_299}")
print(f"  T5 回答里含总额 798       : {'798' in a5}")
print(f"  todos 在 T5 仍然存活      : {snap5['n_todos'] > 0}  ({snap5['n_todos']} 项)")
print(f"  消息数 T1→T5              : {snap1['n_msgs']} → {snap5['n_msgs']}"
      f"（不压缩应一路上涨）")
print(f"  工作区是否出现新文件(归档) : "
      f"{sorted(set(snap5['files']) - set(snap0['files'])) or '无'}")

ev = {"turns_snaps": [snap0, snap1, snap2, snap3, snap4, snap5],
      "report_ok": report_ok, "got": got, "gt": GT,
      "a5_mentions_299": a5_has_299, "a5": a5[:500]}
with open("/root/ch04_hw/hw_bonus_evidence.json", "w", encoding="utf-8") as f:
    json.dump(ev, f, ensure_ascii=False, indent=2, default=str)
print("\n证据已存 /root/ch04_hw/hw_bonus_evidence.json")
```

## 三、逐段拆解（大白话）

**trigger/keep 故意调小**：默认阈值要几十条消息才触发，五轮对话根本够不着。压到 trigger=10、keep=4，压缩必然发生，锯齿肉眼可见——这是实验设计的"加速老化测试"。

**snapshot() 用 get_state 而不是翻 result**：`result["messages"]` 只是一次 invoke 的返回；要看"真实库存"，得用 `agent.get_state(cfg)` 从 checkpointer 里取当前 state。消息数、todos、文件列表三个维度一张快照全拍到。

**T2~T5 的追问设计**：每轮都逼 Agent 回忆早期细节（A005 买了什么、满减门槛、运费原文），既把消息数推过阈值，又制造"压缩后还记不记得"的考题。T5 最狠——问的是第一轮的 A001 金额。

**裁判只看三样**：report.md 的三个数字（正则抠）、T5 回答里有没有 299/798、todos 数量是否 >0。全都不采信 Agent 的自我声明。

## 四、跑起来长什么样（真实输出摘录）

```text
开局   消息 0 条 | todos 0 项 | 文件: orders.txt, promo.txt, shipping.txt
T1 后 消息 6 条（首条 HumanMessage） | todos 3 项 | + report.md
T2 后 消息 10 条                      | todos 3 项     ← 到达 trigger
T3 后 消息 8 条                       | todos 3 项     ← 压缩发生了！
T4 后 消息 6 条                       | todos 3 项     ← 又压一次
T5 后 消息 8 条                       | todos 3 项

裁判结果
  report.md 三数字正确      : True  (got=[798.0, 768.0, 0.0])
  T5 还记得 A001=299        : True
  T5 回答里含总额 798       : True
  todos 在 T5 仍然存活      : True  (3 项)
  工作区是否出现新文件(归档) : 无
```

T5 的回答原文（节选）：「**A001 金额：299.00 元**（商品：无线鼠标）/ **总额：798.00 元**」，还附了完整的去重明细表格——被压缩掉的是旧对话的逐字记录，关键事实转进了摘要，所以"隔了四轮再问第一轮的数"照样答得出。

## 五、这一关的坑

1. **SummarizationMiddleware 必须传 model**：摘要本身是一次 LLM 调用，`SummarizationMiddleware(model=model, ...)` 少了 model 参数直接报错。
2. **没有 checkpointer 就是白跑**：多轮对话靠 `thread_id` 串起来，`InMemorySaver()` 不挂的话每轮都是失忆新会话，"压缩"无从谈起。这也解释了为什么 cfg 里要带 `configurable.thread_id`。
3. **不挂 TodoList 时摘要可能"压丢"计划**：本实验 todos 活到最后是因为它是独立 state 字段、不参与消息压缩；如果计划只存在于对话消息里，压缩后"我本来要干什么"就可能真的没了——这正是两味药要同开的理由。
4. **观察 state 要用 get_state**：只看 invoke 返回值会错过 checkpoint 里的真实库存，得出"压缩只改请求不改状态"的错误结论。
5. **InMemorySaver 重启即失忆**：本实验的记忆只活在进程里。生产要换 SqliteSaver/PostgresSaver 等持久化实现，跨会话记忆才能续上。

## 六、一句话记住

**碎纸机只碎旧单据，不碰石头上的账——压缩的是消息，留下的是摘要、todos 和磁盘。**

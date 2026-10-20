# 第4章作业·Advanced 挑战级 教学详解：A/B 对照，量化规划的价与不值

## 一、这一关到底在考什么

一句话：**同一个任务、同一份数据、同一个模型（temperature=0），唯一变量是"挂不挂 TodoListMiddleware"**，各跑一轮，把工具调用数、消息条数、token 消耗、耗时、正确性五个数摆上台面对比。

作业题干里有句宽容条款："哪怕结果没改善，能解释原因也算挑战完成。"这句话才是本关真正的考点——A/B 实验跑出来 B 轮（规划开）反而多花 6674 个 token、结果没有任何改善，你要能说清**为什么**。做实验只回答一个问题："规划什么时候好"。

比喻：给短跑运动员背上计步器、心率带、录像机，装备全套上了，百米成绩不会变好——因为瓶颈根本不在信息量。规划中间件也一样：它是给"长到会忘事的上下文"准备的装备，三五个文件的小任务，上下文从头到尾一目了然，规划省不了什么，反而多付了装备的"入场费"。

三个关键设计先记在心里：
- **中性任务文案**：TASK 里一个字都不提 write_todos——否则对照组被要求做它做不到的事，两轮输入就不等价了。
- **裁判独立**：正确性由脚本读磁盘 report.md 验数（GT 硬编码 798.00 / 768.00 / 0.00），不信 Agent 自述。
- **只差一个变量**：两轮的工具面完全一致（闭包生成同一套 ls/read_file/write_file），只有 middleware 列表差一项。

## 二、完整代码（注释齐全）

```python
# ============================================================
# 【第4章 作业·Advanced 挑战级】Todo 开 / 关 两轮对照实验
# ============================================================
# 固定输入 + 固定模型（temperature=0），跑两轮同一个任务：
#   轮A（对照组）：不带 TodoListMiddleware
#   轮B（实验组）：带 TodoListMiddleware
# 采集五类数据：工具序列 / 消息数 / token 消耗 / 墙钟时间 /
# 产物正确性（脚本验数，不信自述）。
#
# 关键设计①：TASK 文案必须"中性"——不能提 write_todos，
#   否则两轮的输入就不等价了（对照组会被要求做它做不到的事）。
# 关键设计②：埋雷同 hw_basic（A003 重复行），正确答案固定
#   598.50 / 568.50 / 0.00，两轮用同一个"裁判"脚本验数。
# 关键设计③：挑战级不设"必须B更好"的胜场要求——
#   哪怕没改善，能定位原因（这任务太短，规划省不了什么）
#   也算完成，这正是作业说明的原话精神。
#
# 跑法（WSL）：
#   cd /root/ch04_hw && /root/research_deepagent/.venv/bin/python \
#       /mnt/d/gitcode/learn/deepagents-in-action/task3_ch04/homework/code/hw_advanced.py
# ============================================================
import json, os, shutil, time, re

from dotenv import load_dotenv
load_dotenv("/root/research_deepagent/.env")
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware

MODEL = "deepseek-flash"

def llm():
    return init_chat_model(MODEL, model_provider="openai",
                           temperature=0, max_tokens=8192)

GT = {"dedup": 798.00, "payable": 768.00, "shipping": 0.00}  # 299+159.5+140+60+139.5；满400减30；≥99免运

TASK = ("请核对订单并生成 /workspace/report.md："
        "读 /workspace/orders.csv、/workspace/promo.txt、/workspace/shipping.txt，"
        "注意 order_id 重复的行只计一次；"
        "算出去重后订单总额、优惠后应付金额、运费三个数字写进报告，"
        "报告里三个数字各占一行，格式形如：总额=123.45。最后读回核对一遍。")

ORDERS = """order_id,item,amount
A001,机械键盘,299.00
A002,显示器支架,159.50
A003,USB-C 扩展坞,140.00
A003,USB-C 扩展坞,140.00
A004,鼠标垫,60.00
A005,无线鼠标,139.50
"""
PROMO = "全场满 400 减 30。\n"
SHIPPING = "应付金额满 99 元免运费，否则运费 12 元。\n"

def seed(root):
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root)
    open(f"{root}/orders.csv", "w", encoding="utf-8").write(ORDERS)
    open(f"{root}/promo.txt", "w", encoding="utf-8").write(PROMO)
    open(f"{root}/shipping.txt", "w", encoding="utf-8").write(SHIPPING)

def parse_report(path):
    """裁判：直接读磁盘上的 report.md 拿三个数字。"""
    if not os.path.exists(path):
        return None, None, None
    txt = open(path, encoding="utf-8").read()
    g = lambda p: (float(m.group(1)) if (m := re.search(p, txt)) else None)
    return (g(r"总额[=＝:\s]*(\d+(?:\.\d+)?)"),
            g(r"应付金额[=＝:\s]*(\d+(?:\.\d+)?)"),
            g(r"运费[=＝:\s]*(\d+(?:\.\d+)?)"))

def make_tools(root):
    """闭包工具：两个轮次的工具面完全一致，只有中间件不同。"""
    from langchain_core.tools import tool

    @tool
    def ls() -> str:
        """列出 /workspace 下所有文件名（逗号分隔）。"""
        return ", ".join(sorted(os.listdir(root)))

    @tool
    def read_file(file_name: str) -> str:
        """读取 /workspace 下指定文件的全部内容。file_name 只填文件名。"""
        p = os.path.join(root, file_name)
        if not os.path.exists(p):
            return f"错误：{file_name} 不存在。可用文件：{ls.invoke()}"
        return open(p, encoding="utf-8").read()

    @tool
    def write_file(file_name: str, content: str) -> str:
        """把 content 写入 /workspace 下的 file_name（覆盖写）。"""
        open(os.path.join(root, file_name), "w", encoding="utf-8").write(content)
        return f"已写入 {file_name}（{len(content)} 字符）"

    return [ls, read_file, write_file]

def run_once(with_todo, tag):
    root = f"/root/ch04_hw/adv_{tag}"
    seed(root)                              # 每轮清场重埋，输入严格一致
    mw = []
    if with_todo:
        mw.append(TodoListMiddleware())
    agent = create_agent(llm(), tools=make_tools(root),
                         middleware=mw)
    t0 = time.time()
    r = agent.invoke({"messages": [{"role": "user", "content": TASK}]})
    dt = time.time() - t0
    msgs = r["messages"]
    def _type(m):  # 兼容 BaseMessage 与 dict 两种形态
        return m.get("type") if isinstance(m, dict) else getattr(m, "type", None)
    def _tc(m):
        return (m.get("tool_calls") or []) if isinstance(m, dict) else (m.tool_calls or [])
    def _um(m):
        return (m.get("usage_metadata") or {}) if isinstance(m, dict) else (m.usage_metadata or {})
    def _cname(c):
        return c.get("name") if isinstance(c, dict) else c.name
    tool_seq = [_cname(c) for m in msgs if _type(m) == "ai" for c in _tc(m)]
    usage = {}
    for m in msgs:                          # 累加每条 AI 消息的 token 用量
        if _type(m) == "ai":
            for k, v in _um(m).items():
                if isinstance(v, int):          # 跳过 *_token_details 这类嵌套 dict
                    usage[k] = usage.get(k, 0) + v
    got = parse_report(f"{root}/report.md")
    ok = (got[0] == GT["dedup"] and got[1] == GT["payable"]
          and got[2] == GT["shipping"])
    todos = r.get("todos", [])
    return {"tag": tag, "with_todo": with_todo,
            "tool_seq": tool_seq, "n_tool_calls": len(tool_seq),
            "n_messages": len(msgs),
            "n_write_todos": tool_seq.count("write_todos"),
            "tokens": usage, "seconds": round(dt, 1),
            "report_numbers": got, "correct": ok,
            "todos_final_status": [(t.get("status"), t.get("content")[:24])
                                   for t in todos]}

print("=" * 62)
print("Advanced：Todo 开 / 关 两轮对照（同输入 · 同模型 · 温度 0）")
print("=" * 62)

A = run_once(False, "off")
print(f"\n[轮A · Todo关] 完成：{A['correct']}，工具调用 {A['n_tool_calls']} 次，"
      f"{A['seconds']}s，tokens={A['tokens'].get('total_tokens')}")
print("  工具序列:", A["tool_seq"])

B = run_once(True, "on")
print(f"\n[轮B · Todo开] 完成：{B['correct']}，工具调用 {B['n_tool_calls']} 次，"
      f"{B['seconds']}s，tokens={B['tokens'].get('total_tokens')}")
print("  工具序列:", B["tool_seq"])
print("  todos 终态:", B["todos_final_status"])

print("\n==== 对照表 ====")
rows = [("工具调用次数", "n_tool_calls"), ("消息条数", "n_messages"),
        ("总 token", None), ("耗时(秒)", "seconds")]
for name, key in rows:
    if key:
        print(f"  {name:8s}  A={A[key]!s:>6}  B={B[key]!s:>6}")
    else:
        print(f"  {name:8s}  A={A['tokens'].get('total_tokens'):>6}  "
              f"B={B['tokens'].get('total_tokens'):>6}")
print(f"  产物正确   A={A['correct']}  B={B['correct']}")

d_tools = B["n_tool_calls"] - A["n_tool_calls"]
d_tok = (B["tokens"].get("total_tokens") or 0) - (A["tokens"].get("total_tokens") or 0)
print(f"\nΔ(B-A)：工具 {d_tools:+d} 次，token {d_tok:+d}")

analysis = []
if B["n_write_todos"] > 0:
    analysis.append(f"B 轮 write_todos 调用 {B['n_write_todos']} 次（规划真实发生了）")
else:
    analysis.append("B 轮一次 write_todos 都没调——中间件只给能力，用不用还是模型决定")
if B["correct"] and A["correct"]:
    analysis.append("两轮产物都对：这种 3 文件 + 1 产物的短任务，"
                    "上下文根本不会长到'忘事'，规划的收益自然显示不出来")
elif B["correct"] and not A["correct"]:
    analysis.append("B 对 A 错：Todo 在这轮立了功（去重雷被 B 抓住而 A 漏了）")
elif A["correct"] and not B["correct"]:
    analysis.append("A 对 B 错：规划不是万能药——清单画了勾也可能算错数")
else:
    analysis.append("两轮都错：查 report.md 排雷细节")
print("\n==== 解释（挑战级的完成标准：能解释就算完成）====")
for a in analysis:
    print("  -", a)

ev = {"task": TASK, "ground_truth": GT,
      "round_off": A, "round_on": B,
      "delta": {"tools": d_tools, "tokens": d_tok},
      "analysis": analysis}
with open("hw_advanced_evidence.json", "w", encoding="utf-8") as f:
    json.dump(ev, f, ensure_ascii=False, indent=2, default=str)
print("\n证据已存 /root/ch04_hw/hw_advanced_evidence.json")
```

## 三、逐段拆解（大白话）

**中性 TASK 文案**：对照实验的铁律是"一次只改一个变量"。轮A没有 write_todos 工具，如果 TASK 里写"请先列计划"，轮A就收到了一条它无法完整执行的指令——变量就不止中间件一个了。所以挑战级的任务文案对规划只字不提。

**闭包 make_tools(root)**：每轮调用生成一套绑定自己目录的工具。工具面（ls/read_file/write_file）两轮完全相同，杜绝"工具不同导致行为差异"的解释空间。

**seed(root) 每轮清场**：A 轮跑完 report.md 已存在；不清场，B 轮 Agent 可能直接读旧报告交差，"实验组做对照组的卷子"。

**usage_metadata 累加**：token 数就藏在本地：遍历 transcript 里每条 AI 消息的 `usage_metadata`，把 `input_tokens`/`output_tokens`/`total_tokens` 加起来（`isinstance(v, int)` 顺手跳过嵌套的 token_details 字典）。这是langchain 生态里"本地就能算清成本"的标准姿势。

**四分支 analysis**：脚本按两轮对错组合自动生成解释——B对A错→规划立功；A对B错→规划不是万能药；都对→短任务无收益；都错→查雷。本跑落在"都对"分支，于是那句"上下文根本不会长到忘事"的解释被自动选中存档。注意 analysis 的判定逻辑让"没改善"也能被程序化地"说清楚"——这就是题干宽容条款的代码化。

## 四、跑起来长什么样（真实输出摘录）

```
[轮A · Todo关] 完成：True，工具调用 6 次，7.2s，tokens=5184
  工具序列: ['ls', 'read_file', 'read_file', 'read_file', 'write_file', 'read_file']

[轮B · Todo开] 完成：True，工具调用 6 次，7.0s，tokens=11858
  工具序列: ['ls', 'read_file', 'read_file', 'read_file', 'write_file', 'read_file']
  todos 终态: []

==== 对照表 ====
  工具调用次数  A=     6  B=     6
  消息条数      A=    12  B=    12
  总 token      A=  5184  B= 11858
  耗时(秒)      A=   7.2  B=   7.0
  产物正确   A=True  B=True

Δ(B-A)：工具 +0 次，token +6674

==== 解释（挑战级的完成标准：能解释就算完成）====
  - B 轮一次 write_todos 都没调——中间件只给能力，用不用还是模型决定
  - 两轮产物都对：这种 3 文件 + 1 产物的短任务，上下文根本不会长到'忘事'，
    规划的收益自然显示不出来
```

两份 report 原件（`evidence/hw_advanced_report_todo_off.md` 与 `..._todo_on.md`）内容一致：总额=798.00、应付金额=768.00、运费=0.00，A003 的 140.00 只计了一次。

## 五、这一关的坑

1. **token 对比别只看总数**：B 轮多出的 6674 个 token 几乎全是 input——系统提示里的计划规程 + write_todos 的 schema 注入，属于"装了装备的入场费"，而且**每轮请求都收一次**。真正用没用还得看 `n_write_todos`。
2. **"开了中间件=会用"是错觉**：TodoListMiddleware 只是把工具和规程放进上下文，调不调用是模型的自由裁量。deepseek-flash 在这个短任务上干脆没列计划——别把"没调用"误判成"中间件坏了"。
3. **变量污染**：忘了清场、TASK 里提了 write_todos、两轮用不同 max_tokens/temperature，任何一个都会让"Δ 6674"这个数字失去解释力。
4. **温度不是 0 时结论不稳**：采样随机性会把工具序列和 token 数搅出噪声，"差异是中间件造成"的归因就不干净了。对照实验必须钉死 temperature=0。

## 六、一句话记住

**规划是给"会忘事的长度"准备的装备——短任务上它只收入场费，不返现；能不能收回来，要看上下文长不长。**

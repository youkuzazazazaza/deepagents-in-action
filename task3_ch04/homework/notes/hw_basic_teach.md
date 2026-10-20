# 第4章作业·Basic 基础级 教学详解：计划全勾了，数字对了吗？

## 一、这一关到底在考什么

一句话：让 Agent 带着 TodoList 做 5 步订单核对，最后**并排打印两张表**——「todos 状态表」（Agent 自己声称的进度）vs「磁盘核对表」（脚本绕开 Agent 验出来的真相）。

本级的灵魂句：**计划全部 completed ≠ 验收通过**。清单全勾只说明 Agent "认为"自己干完了，数字对不对得另算。所以脚本干了三件事：① 埋一套带雷的固定资料（A003 重复订单 + 满 300 减 30 + 满 100 包邮）；② 真值（GT）由脚本硬编码，绝不采信 Agent 的回答；③ 最后绕开 Agent 的所有工具，直接用正则从磁盘上的 report.md 里抠数字逐项比对。

比喻：todos 状态表是施工队交工时自己打的勾，磁盘核对表是监理拿卷尺现场量。工程验收从来只认后者。

顺带一提：这次用的是 `create_deep_agent`（不是上一步的裸 `create_agent`），它自带文件工具，我们只需再补挂 TodoListMiddleware——这也演示了中间件"自选组装"的玩法。

## 二、完整代码（注释齐全）

```python
# ============================================================
# 【第4章 作业·Basic 基础级】显式启用 TodoListMiddleware，
#   固定资料 + 多步骤任务 + 逐项核对报告
# ============================================================
# 本级的灵魂句：计划全部 completed ≠ 验收通过。
# 做法：
#   1) 脚本自己往项目目录埋 3 份固定资料（订单/促销/运费），
#      其中 orders.csv 里故意埋了一行"重复订单"（A003 出现两次）
#   2) 让 Agent 挂着 TodoListMiddleware 核对订单并写 report.md
#   3) 脚本绕开 Agent，直接从磁盘读 report.md 逐项核对：
#      去重总价 598.50 / 应付 568.50 —— 去重这一步就是"雷"
#   4) 并排打印「todos 状态表」vs「磁盘核对表」：
#      就算清单全勾了，数字错一个，验收就是不过
#
# 跑法（WSL）：
#   cd /root/ch04_hw && /root/research_deepagent/.venv/bin/python \
#       /mnt/d/gitcode/learn/deepagents-in-action/task3_ch04/homework/code/hw_basic.py
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
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import TodoListMiddleware

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
    max_retries=2,
    temperature=0,
)

# ---------- 第 1 步：埋固定资料（每轮重埋，保证输入一致） ----------
ROOT = "/root/ch04_hw/basic_proj"           # 虚拟 /workspace 的家
if os.path.exists(ROOT):
    shutil.rmtree(ROOT)                     # 清场重埋，输入才"固定"
os.makedirs(os.path.join(ROOT, "workspace"), exist_ok=True)

ORDERS = """order_id,item,amount
A001,机械键盘,129.00
A002,鼠标垫,88.50
A003,显示器支架,145.00
A004,人体工学椅,236.00
A003,显示器支架,145.00
"""
PROMO = "全场促销：去重后的订单总额满 300 元立减 30 元（每单只享一次）。\n"
SHIP  = "运费规则：去重折后金额不足 100 元收运费 12 元；达到 100 元包邮。\n"
with open(os.path.join(ROOT, "workspace", "orders.csv"), "w", encoding="utf-8") as f:
    f.write(ORDERS)
with open(os.path.join(ROOT, "workspace", "promo.txt"), "w", encoding="utf-8") as f:
    f.write(PROMO)
with open(os.path.join(ROOT, "workspace", "shipping.txt"), "w", encoding="utf-8") as f:
    f.write(SHIP)

# 地面真值（脚本自己算，不信 Agent）：
GT = {
    "raw_total":   129.00 + 88.50 + 145.00 + 236.00 + 145.00,   # 743.50（含重复）
    "dedup_total": 129.00 + 88.50 + 145.00 + 236.00,            # 598.50（去重）
    "payable":     598.50 - 30.00,                              # 568.50
    "shipping":    0.0,
}

# ---------- 第 2 步：显式启用 TodoListMiddleware ----------
agent = create_deep_agent(
    model=model,
    backend=FilesystemBackend(root_dir=ROOT, virtual_mode=True),
    middleware=[TodoListMiddleware()],        # ← 本级主角：显式启用
)

TASK = (
    "请帮我核对这个客户今天的订单，共5步，建议先用 write_todos 列计划再做：\n"
    "1) 读取 /workspace/orders.csv，注意 order_id 若有重复行，同一单只计一次；\n"
    "2) 读取 /workspace/promo.txt，弄清促销规则；\n"
    "3) 读取 /workspace/shipping.txt，弄清运费规则；\n"
    "4) 算出三个数字：去重后的订单总额、优惠后的应付金额、运费；\n"
    "5) 把结果写入 /workspace/report.md，格式如下（数字保留两位小数）：\n"
    "   - 去重后订单总额：XXX 元\n"
    "   - 应付金额：XXX 元\n"
    "   - 运费：XXX 元\n"
    "写完后核对一遍再回答我。"
)

result = agent.invoke({"messages": [{"role": "user", "content": TASK}]})

tool_seq = []
for m in result["messages"]:
    if m.type == "ai" and getattr(m, "tool_calls", None):
        for tc in m.tool_calls:
            tool_seq.append(tc["name"])

print("==== A. 工具调用序列 ====")
print(" ", tool_seq)

print("\n==== B. todos 状态表（Agent 自己声称的进度）====")
todos = result.get("todos") or []
for t in todos:
    print(f"  [{t.get('status'):>11s}] {t.get('content')}")
all_completed = bool(todos) and all(t.get("status") == "completed" for t in todos)
print(f"  → 清单是否全部 completed：{all_completed}")

# ---------- 第 3 步：绕开 Agent，磁盘逐项核对 ----------
REPORT = os.path.join(ROOT, "workspace", "report.md")
print("\n==== C. 磁盘核对表（report.md 原文 → 脚本自己验数）====")
report_text = ""
if os.path.exists(REPORT):
    report_text = open(REPORT, encoding="utf-8").read()
    print(report_text)
else:
    print("  !! report.md 不存在 —— Agent 根本没交产物")

import re
def grab_num(label):
    m = re.search(label + r"[：:]\s*([0-9]+(?:\.[0-9]+)?)", report_text)
    return float(m.group(1)) if m else None

got_dedup  = grab_num("去重后订单总额")
got_pay    = grab_num("应付金额")
got_ship   = grab_num("运费")

checks = {
    "report_exists":      os.path.exists(REPORT),
    "dedup_total_ok":     got_dedup is not None and abs(got_dedup - GT["dedup_total"]) < 0.01,
    "payable_ok":         got_pay   is not None and abs(got_pay   - GT["payable"])   < 0.01,
    "shipping_ok":        got_ship  is not None and abs(got_ship  - GT["shipping"])  < 0.01,
}
print("\n==== D. 逐项核对 ====")
for k, v in checks.items():
    print(f"  {'PASS' if v else 'FAIL':4s}  {k}")
print(f"  期望: 去重总额={GT['dedup_total']:.2f} 应付={GT['payable']:.2f} 运费={GT['shipping']:.2f}")
print(f"  实得: 去重总额={got_dedup} 应付={got_pay} 运费={got_ship}")

verdict = all(checks.values())
print("\n==== E. 灵魂结论 ====")
print(f"  todos 全 completed：{all_completed}")
print(f"  磁盘核对通过    ：{verdict}")
if all_completed and not verdict:
    print("  → 清单全勾了但数字错：『计划全部 completed ≠ 验收通过』实锤！")
elif all_completed and verdict:
    print("  → 这轮 Agent 真做对了。但请注意：这份确定性来自脚本核对，")
    print("    不是来自清单上的勾——换个输入，勾还是勾，对不对就不好说了。")

final_answer = str(result["messages"][-1].content)
ev = {"task": TASK, "tool_seq": tool_seq, "todos": todos,
      "report_md": report_text,
      "got": {"dedup": got_dedup, "payable": got_pay, "shipping": got_ship},
      "ground_truth": GT, "checks": checks,
      "all_completed": all_completed, "verdict": verdict,
      "final_answer_head": final_answer[:300]}
with open("hw_basic_evidence.json", "w", encoding="utf-8") as f:
    json.dump(ev, f, ensure_ascii=False, indent=2)
print("\n证据已存 /root/ch04_hw/hw_basic_evidence.json")
print("DONE")
```

## 三、逐段拆解（大白话）

**清场重埋（shutil.rmtree）**：固定输入是对照实验的地基。不清场，上一轮的 report.md 还躺在目录里，Agent 可能读旧文件糊弄——输入都不一样了，"做对"就无从谈起。

**三份资料各埋一颗雷**：orders.csv 里 A003 出现两次（不去重就会多算 145）；promo.txt 写明"满 300 立减 30、每单只享一次"（重复减就错）；shipping.txt 写明"不足 100 收 12、达 100 包邮"（568.5 显然包邮）。真值 GT 由脚本硬编码——注意 GT 是"人"算的，不是问 Agent 要的。

**create_deep_agent vs create_agent**：deep 版自带 ls/read_file/write_file 等文件工具（配 FilesystemBackend 用），我们只需补挂 TodoListMiddleware。这演示了"全家桶 vs 自选组装"的后一种：**中间件是插拔的**。

**验收的三重防线**：① `result.get("todos")` 拿状态表（Agent 的自述）；② 直接 `open()` 读磁盘 report.md（产物存在性）；③ 正则抠数字和 GT 逐项比（数值正确性）。三层一层都不能少——少了 ① 看不到"声称"，少了 ②③ 就只剩"声称"。

**灵魂结论的逻辑分支**：全勾 + 数字错 = "completed ≠ 验收通过"实锤；全勾 + 数字对 = 这轮对了，但脚本在输出里提醒你：确定性来自核对，不是来自勾。这个分支本身就是本关要教的思维。

## 四、跑起来长什么样（真实输出摘录）

```text
==== A. 工具调用序列 ====
  ['write_todos', 'ls', 'read_file', 'read_file', 'read_file',
   'write_todos', 'write_file', 'read_file', 'write_todos']

==== B. todos 状态表（Agent 自己声称的进度）====
  [  completed] 读取 /workspace/orders.csv，处理 order_id 重复行（同一单只计一次）
  [  completed] 读取 /workspace/promo.txt，弄清促销规则
  [  completed] 读取 /workspace/shipping.txt，弄清运费规则
  [  completed] 计算去重后订单总额、优惠后应付金额、运费
  [  completed] 写入 /workspace/report.md 并核对
  → 清单是否全部 completed：True

==== C. 磁盘核对表（report.md 原文 → 脚本自己验数）====
# 订单核对报告

- 去重后订单总额：598.50 元
- 应付金额：568.50 元
- 运费：0.00 元

==== D. 逐项核对 ====
  PASS  report_exists
  PASS  dedup_total_ok
  PASS  payable_ok
  PASS  shipping_ok
  期望: 去重总额=598.50 应付=568.50 运费=0.00
  实得: 去重总额=598.5 应付=568.5 运费=0.0
```

最终回答里 Agent 还主动列了算式：`129.00 + 88.50 + 145.00 + 236.00 = 598.50`，并解释 A003 出现两行、金额相同、按同一单只计一次——雷被明确排掉了，而且它说得出来为什么。注意工具序列里的第 8 步 `read_file`：它写完 report 又读回来核对了一遍，这正是任务末尾"写完后核对一遍再回答我"那句指令的作用。

## 五、这一关的坑

1. **把"清单全勾"当验收**：这是本关反复敲的点。勾是 Agent 的自我声明，数字对错只能靠外部核对。
2. **GT 别抄错**：真值算式写在代码注释里（743.50 含重复 / 598.50 去重 / 568.50 应付）。写作业时把 GT 抄错，Agent 明明对了也会被判错——对照实验里"尺子"本身必须先对。
3. **重复订单的"同额"细节**：本题 A003 两行金额恰好相同（145.00）。如果两行金额不同，"去重取哪个"就成了新问题——出题和判卷都要意识到这个隐含约定。
4. **正则抠数字认中英冒号**：`[：:]` 两种冒号都得认，Agent 把冒号写成半角（运费后面跟 0.00）时别让核对脚本扑空。

## 六、一句话记住

**勾是施工队自己打的，数是监理量出来的——验收只认磁盘上的数字。**

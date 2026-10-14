# 04 · Advanced：向 add 工具发射"炮弹"（冲优秀作业）

> 状态：**已实测 ✅**（2026-10-14，三发炮弹全部上靶，原始数据见 `notes/evidence/`）

---

## 一、这一关验证什么

打卡要求：对 `add` 工具发**空输入**和**超长输入**，比一比结果，讲清「工具请求 → 执行 → 返回」之间的关系，留一条 Trace 作证据。

**本质**：这是在测试 Agent 的**防御性**——真实的用户不会按说明书输入，工程上的鲁棒性就体现在边界条件下。

## 二、三发炮弹（实测设计）

| 炮弹 | 输入 | 预期考点 |
|---|---|---|
| normal | `12345.678 + 8765.432` | baseline 标准链路 |
| empty | "请用 add 计算总和"（不给数字） | 会硬编数字还是反问？ |
| huge | `12345.678 + 400个9` | 工具 schema 顶不顶得住？模型心算还是搬运？ |

发射器：`code/adv_fire.py`（与 run_basic.py 同构，httpx 裸 HTTP，可单发：`python adv_fire.py huge`）

## 三、实测结果总表

| 炮弹 | 耗时 | add 被调? | 结果 | 一句话结论 |
|---|---|---|---|---|
| normal | 10.4s | ✅ 1次 | `21111.11` ✅ | 标准链路：点单→执行→答对 |
| empty | 19.1s | ❌ 0次 | 先 `ls /` 探索，然后**反问用户要数字** | 防御性满分：不硬编、不瞎调 |
| huge | >300s 客户端超时 | ⚠️ 调了但被**拒收** | 服务端自救 27 条消息后给出答案，但**答案错了** | 全场最佳教学案例，见下文 |

## 四、huge 炮弹五幕剧（27 条消息实录）

400 个 9 ≈ 10^400，远超 float64 上限（~1.8×10^308）。`add(a: float, b: float)` 的
args schema 在校验层直接**拒收**——第一道防线是**类型系统**，不是代码逻辑。

### 深挖：这个 schema 是哪来的？框架自带的吗？（源码考古，实测 2026-10-14）

**不是框架现成自带的，是从你写的函数定义自动"派生"出来的**。源头在主项目源码：

```python
# /root/research_deepagent/src/research_deepagent/tools.py
@tool(parse_docstring=True)            # ← 机制：LangChain 的装饰器（框架给的）
def add(a: float, b: float) -> float:  # ← 内容：你自己写的签名 + docstring
    """Add two numbers precisely and return the sum.
    Use this tool for any arithmetic addition instead of computing yourself.

    Args:
        a: First number.
        b: Second number.
    """
    return a + b
```

派生链路：`@tool` 读**函数签名 + docstring** → **pydantic** 建模成 `AddInput` 类 →
`model_json_schema()` 序列化成 JSON。现场打印 `add.args_schema.model_json_schema()` 的真实产物：

```json
{"description": "Add two numbers precisely and return the sum. Use this tool
  for any arithmetic addition instead of computing yourself.",   // ← docstring 第一段
 "properties": {
   "a": {"description": "First number.", "type": "number"},       // ← Args 段逐条
   "b": {"description": "Second number.", "type": "number"}},     //    映射成参数说明
 "required": ["a", "b"], "title": "add", "type": "object"}
```

这份 JSON 就是随每次请求发给 LLM 的"工具说明书"。**机制框架自带（LangChain
@tool + pydantic），内容由你的函数定义决定**——改一个类型注解或 docstring，
LLM 看到的说明书立刻跟着变。这就是第 02 篇"类型注解是写给 LLM 看的"的底层实现。

### 拒收的精确路径（对照实验，比想象的有料）

LLM 发的 tool_call 参数是 **JSON number**，路径拆开看（probe 实测）：

| 路径 | 发生了什么 | 结果 |
|---|---|---|
| JSON number `999…`（400位） | `json.loads` 解析成 **Python int**（无限精度）→ pydantic int→float 溢出 | ❌ `ValidationError: Input should be a valid number` **被拒** |
| 假如发字符串 `"999…"` | pydantic str→float 强转 | ⚠️ **放行为 `inf`**，`add(1.5, inf)` 静默返回 `inf`（错值不报错） |

即：挡住炮弹的是 **JSON number→int→float 这条转换链**；但 schema 防御是**不对称**的——
字符串形态的超大数会漏网成 `inf`。生产级数值工具应加
`Annotated[float, Field(allow_inf_nan=False)]` 才严实。

被拒后 Agent 没有报错躺平，而是上演自救五部曲（完整消息流见 `evidence/huge_state.json`）：

1. **存证**：`write_file` 把 400 个 9 写进 `/number_b.txt`
2. **数数**：`grep ^.{105}$` 二分探测长度 → 发现 grep 计的是"行数"不是"字符数"（工具行为认知修正）
3. **灵光**：`edit_file` 把每个 `9` 替换成 `9\n` → "replaced **400** instances" —— **精确数出 400 个 9**！
4. **验算**：`add(999999, 12345.678)`、`add(12344.678, 1)` 等小数字验证进位模式（全对）
5. **收尾**：`delete` 删临时文件，输出 LaTeX 公式 + 完整数字

**但最后一步翻车了**（Python 精确验证）：

```
真值        = 10^400 + 12344.678 = '1' + 395个0 + '12344.678'  （405 字符）
AI 代码块答案 = 621 字符：形式对（1...12344.678），中间 0 多打了 216 个
AI 自述矛盾：LaTeX 说"355 个零"、正文说"409-digit"、代码块实际 621 字符 —— 三个数互不相等
```

另外还 spawn 出子线程 `0c2bf7da`（开场即估算错误"~10^603"），客户端断连后仍
`status=running` 挂着（僵尸 run），主线程 run 标 `error` 但消息完整落盘。

### 第二轮复测（同环境隔 30 分钟，亲手复跑）

| 炮弹 | 耗时 | 表现 | 对比第一轮 |
|---|---|---|---|
| normal | 9.7s | ✅ 忠实点单 → `21111.11` | 两次一致 |
| empty | 41.8s | ✅ `ls` → `glob` 翻全盘 → 回答"环境为空，没有可加的数" | 第一轮 19.1s 只 `ls` 后**反问**；这轮选择**翻抽屉找证据再陈述**——路径不同，**底线相同：都没瞎编数字** |
| huge | 客户端中途 Ctrl-C | 服务端照跑：17 条消息（含 todo list 规划），最终答 `10²⁵⁸ + 12344.678` | **又错，错法还不同**：第一轮抄多 216 个零（621 位），这轮直接把 400 个 9 **当成 258 位** |

三个新结论：

1. **同一个 Agent 同一个问题，两次走不同的路**：LLM 每次动脑路径像"抽签"（temperature>0 的
   随机采样），但"不瞎编数字"这类底线行为是稳的。→ 测 Agent 要多跑几轮看**底线**稳不稳，
   别只看单次路径。
2. **两轮 huge 全翻车、错法各异**：证明"让 LLM 手写几百位长数字"是**结构性死穴**（不是运气）。
   正确工程做法：数值让工具算好、**以字符串原样透传**，禁止模型誊写。
3. **Ctrl-C 停不掉服务端**：客户端中断 ≈ 电话挂断，对方（服务端 run）继续干完活才落盘——
   这就是"客户端超时/报错 ≠ 任务失败"，排查时永远要看服务端 state。

## 五、验证脚本（证据可复算）

```python
# 真值 = 12345.678 + (10^400 - 1) = 10^400 + 12344.678
truth = '1' + '0'*395 + '12344.678'
import re
final = [m for m in state['values']['messages']
         if m['type']=='ai' and not m.get('tool_calls')][-1]['content']
ai_num = re.findall(r'[0-9]{50,}(?:\.[0-9]+)?', final)[0]
print(ai_num == truth)   # False：621 字符 vs 405 字符
```

## 六、三条工程启示（本关灵魂）

1. **Schema 就是防御工事（但有不对称漏洞）**：`a: float` 四个字符挡住了 10^400 的
   炮弹——校验发生在工具执行**之前**，「请求 → 执行 → 返回」里"执行"环节自带闸门。
   且 schema 不是天上掉的：`@tool` 从你的签名+docstring **派生**（见第四节考古）。
   但注意：字符串形态的超大数会被 str→float 强转成 `inf` **静默漏网**——校验要
   严实得自己加 `allow_inf_nan=False`。
2. **工具可靠 ≠ 输出可靠**：Agent 用工具数清了 400、验证了进位，方法全对；但最后
   "手写"621 位长数字时 LLM 数感崩溃（多打 216 个零）。**长数值必须让工具生成并
   直传，不能让模型誊写**——这是真实生产里血泪级教训。
3. **边界输入 = Agent 行为放大器**：一发炮弹炸出探索（empty）、自救（huge）、僵尸
   run（断连不灭）三种平时看不见的行为。压测 Agent 就要打这类输入。

## 七、LangSmith Trace 证据

`.env` 已配 `LANGSMITH_TRACING=true`，三发炮弹自动上报云端。打开
smith.langchain.com → Projects → `research`，按时间 14:53 前后可看到：
- empty 的 trace 树：`ls` 节点 → 反问（无 add 节点）
- huge 的 trace 树：add 拒收 → write/grep/edit_file 链 → 超长最终消息

## 八、Step 4 预告：双模型对撞（学有余力）

`.env` 里 `AGENTSEEK_MODEL` 切换 `glm-5.3` ↔ `deepseek-flash`，同一个问题跑两遍，比：

1. **工具调用稳不稳**：谁从不心算、永远忠实点单？
2. **边界行为**：空输入谁会反问、谁会硬编数字？400 个 9 谁输出得更准？
3. **速度与 token**：LangSmith 里直接看两家耗时/花销。

---

> 📌 证据文件：`evidence/adv_normal.json` / `adv_empty.json` / `huge_state.json`（服务端原始 state，可复算一切）；发射器 `code/adv_fire.py`。

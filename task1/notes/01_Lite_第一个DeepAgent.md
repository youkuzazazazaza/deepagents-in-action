# 01 · Lite 级：跑通你的第一个 Deep Agent

> 对应教程：[ch02-quickstart](https://datawhalechina.github.io/deepagents-in-action/chapters/ch02-quickstart/)
> 代码：本仓库 `code/lite_agent.py`（小白注释版，每行都有说明）
> 实际运行位置：WSL Ubuntu 的 `/root/ch02_lite/lite_agent.py`

---

## 一、这一关学什么

**一句话**：你写一个普通的 Python 函数 `add()`，让大模型"隔着空气"指挥它算数——而大模型自己从头到尾**没算过任何数**。

跑完你会得到 4 条消息的轨迹（Trace），这就是打卡证据：

```
① human : 你提问 "用 add 工具算 12345.678 + 8765.432"
② ai    : 大模型决定 → 我要调 add(a=12345.678, b=8765.432)
③ tool  : 你的 Python 函数【真的执行】→ 21111.11
④ ai    : 大模型拿到结果，组织语言回答你
```

## 二、先修概念（大白话版）

### 2.1 Agent 的本质：点菜与炒菜

- **大模型 = 服务员**：会读菜单、会点单，但不会炒菜（让它心算 `12345.678+8765.432` 它可能算错——它是个"语言艺术家"，不是计算器）
- **工具（Tool）= 后厨的菜**：你用 Python 写的普通函数
- **Agent = 餐厅**：把服务员和后厨组装在一起的那套机制

大模型"调用工具"，实际发生的是：**它输出一段结构化的"点菜单"（工具名+参数），Agent 框架截住这张单子，在你的电脑上真正执行函数，再把结果端回给大模型看。**

### 2.2 一个函数想被 Agent 调用，需要满足三要素（本章核心考点）

| 要素 | 在代码里长什么样 | 大模型拿它干什么用 |
|---|---|---|
| ① 清晰的功能描述 | 函数下第一行的 docstring `"""Add two numbers..."""` | 决定**什么时候**用这个工具 |
| ② 类型注解的参数 | `a: float, b: float` | 知道**怎么传参**（传几个、什么类型） |
| ③ 明确的返回值 | `-> float` | 知道拿回的东西是什么，怎么接着用 |

### 2.3 args schema 是什么？

把三要素翻译成一张"参数说明书"，自动生成、大模型可读：

```json
{
  "name": "add",
  "description": "Add two numbers precisely and return the sum.",
  "parameters": {
    "type": "object",
    "properties": {
      "a": {"type": "number"},
      "b": {"type": "number"}
    },
    "required": ["a", "b"]
  }
}
```

大模型就是照着这张说明书**生成 JSON 参数**的。类型注解越准确，传参越稳——这就是为什么 `a: float` 不能省。

## 三、动手前 60 秒：确认环境

在 **WSL Ubuntu 终端**里依次执行（`$` 开头的是命令，不用输）：

```bash
$ cd /root/ch02_lite        # 进入教学目录
$ python -V                 # 应显示 Python 3.x（已配好全局 venv）
$ cat lite_agent.py | head -15   # 瞄一眼代码开头
```

> ⚠️ Key 不用你操心：`lite_agent.py` 第 32 行会自动去主项目 `/root/research_deepagent/.env` 读取（**Key 永远不写进代码和本仓库**）。

## 四、代码全景：一共 7 步

`code/lite_agent.py` 总共 97 行，路线图：

```
第0步  读取 .env（把 API Key 装进环境变量）      → 24-32 行
第1步  进口两个主角：模型客户端 + 装配车间        → 37-38 行
第2步  定义工具 add()（三要素齐全）              → 46-51 行
第3步  配置大模型（glm-5.3，思考型，给足耐心）    → 55-61 行
第4步  组装 Agent（一行 create_deep_agent）      → 64-70 行
第5步  发起请求 invoke()                        → 73-77 行
第6步  打印 4 条消息轨迹                        → 82-92 行
第7步  存 Trace 证据到 trace.json               → 95-97 行
```

### 精讲 ①：为什么第 0 步要自己写 load_env？

因为教学代码想让你**看穿** `load_dotenv()` 的黑盒——它就是逐行读文件、按第一个 `=` 切开、塞进 `os.environ`。`setdefault` 的意思是：**系统里已有的变量优先，不覆盖**（防止你临时 export 的测试值被文件冲掉）。

### 精讲 ②：`tools=[add]` 挂的是裸函数？

对，不用写 `@tool` 装饰器。`create_deep_agent` 会自动把裸函数包装成工具——读它的 docstring 当描述、读类型注解当参数说明书（就是 2.3 那张表）。

### 精讲 ③：`system_prompt` 那句话为什么必须写？

`"Always use the add tool for arithmetic instead of computing yourself."`

不写的话，大模型很可能**直接心算**然后答错或答对全凭运气。系统提示词 = 给服务员立规矩："算术必须下单给后厨，禁止自己心算。"

### 精讲 ④：`invoke()` 不是"一次对话"那么简单

`agent.invoke({...})` 内部是一个**循环**：模型说话 → 有工具调用？→ 执行 → 把结果喂回去 → 模型再说……直到模型不再点工具、给出最终回答。你看到的 4 条消息，就是这场循环的完整留痕。

## 五、跑！

```bash
$ cd /root/ch02_lite
$ python lite_agent.py
```

（首次约 10~40 秒；glm-5.3 是思考模型，会先"想"再动）

## 六、预期输出（跑对了长这样）

```
[REQUEST] Please use the add tool to compute 12345.678 + 8765.432, then tell me the result.
[TOOL EXEC] add(a=12345.678, b=8765.432) -> 21111.11     ← 铁证：你的函数真的被执行了
==== MESSAGE TRACE ====
- human        name=       content='Please use the add tool to compute 12345.678 + 8765.432...' tool_calls=None
- ai           name=       content='' tool_calls=[('add', {'a': 12345.678, 'b': 8765.432})]   ← 点菜单
- tool         name=add    content='21111.11' tool_calls=None                              ← 后厨出菜
- ai           name=       content='12345.678 + 8765.432 = 21111.11 ...' tool_calls=None    ← 服务员上菜
[SAVED] /root/ch02_lite/trace.json
```

**打卡对照**：`[TOOL EXEC]` 那行 = 请求→执行→返回里的"执行"；`tool` 消息 = "返回"；两条 `ai` 消息夹着它 = 完整闭环。

## 七、常见坑 FAQ

| 症状 | 原因 | 解法 |
|---|---|---|
| `KeyError: 'OPENAI_API_KEY'` | .env 没读到（路径不对/文件没了） | 确认 `/root/research_deepagent/.env` 存在，第 32 行路径没改 |
| 跑了很久然后超时 | glm-5.3 思考中，默认超时太短 | 代码里已设 `timeout=240`，别改小 |
| 大模型直接说了答案，没有 tool 消息 | system_prompt 没强调"必须用工具" | 保留那句 "Always use the add tool..." |
| `ai` 消息 content 是空的 | 正常！点工具的那轮发言只有 tool_calls 没有正文 | 看 `tool_calls=[...]` 而不是 content |

## 八、自测 3 题（下一关前过一遍）

1. 大模型"调用" `add` 时，到底是谁在执行这个函数？在谁的电脑上？
2. 把 `a: float` 改成 `a` （无注解），args schema 会发生什么？大模型传参可能出什么问题？
3. 4 条消息里，哪条是"点菜单"？哪条是"菜"？

<details>
<summary>参考答案（先自己答再看）</summary>

1. **你的电脑上的 Python 进程**。大模型只输出了"点菜单"（工具名+参数 JSON），Agent 框架截住它并在本地执行，结果再喂回去。
2. schema 里 `a` 的类型信息丢失（变成任意类型），大模型可能传字符串 `"12345.678"` 或传错位置，函数执行报错或不稳定。
3. `ai`(带 tool_calls) 是点菜单；`tool`(name=add, content=21111.11) 是菜。
</details>

---

## 下一关预告

Lite 有个致命局限：agent 活在你的**脚本进程里**，脚本跑完就没了——每跑一次都要重新启动一次大模型连接，没法"续桌"，更没法让别人也来点菜。

**02 · Basic 级**：把 agent 搬进常驻服务进程，走 HTTP 隔空使唤——所有 AI 产品的真实架构形态。

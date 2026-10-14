# ============================================================
# 【第2章 Lite 打卡级】第一个 Deep Agent + 自定义工具
# ============================================================
# 目标：你写一个普通 Python 函数 add()，让大模型"调用"它算数。
#
# 完整链路（跑完后看输出，正好 4 条消息）：
#   ① human  : 你提问 "用 add 工具算 12345.678 + 8765.432"
#   ② ai     : 大模型决定 -> 我要调 add(a=12345.678, b=8765.432)
#   ③ tool   : 你的 Python 函数【真的执行】-> 21111.11
#   ④ ai     : 大模型拿到结果，组织语言回答
#
# 关键认知：大模型从头到尾没算过数！它只是"点菜的服务员"，
#          真正"炒菜"的是你本地的函数。这就是 Agent 的本质。
# ============================================================

import os, json

# ---------- 第 0 步：加载 .env 里的 API Key ----------
# .env 文件长这样（KEY=VALUE 一行一个）：
#   OPENAI_API_KEY=sk-xxx
#   OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4
# 下面这个函数就是手动版 load_dotenv()：
#   逐行读文件，跳过注释和空行，把 KEY=VALUE 塞进环境变量 os.environ
def load_env(p):
    for line in open(p):
        line = line.strip()                      # 去掉首尾空格/换行
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)            # 只按第一个 = 切开
            os.environ.setdefault(k, v.strip())  # setdefault=已存在则不覆盖

# 你的 Key 就放在主项目的 .env 里（一个字都不用改）
load_env("/root/research_deepagent/.env")

# ---------- 第 1 步：导入两个主角 ----------
# ChatOpenAI    : "大模型客户端"（兼容 OpenAI 接口的都行，这里用智谱 GLM）
# create_deep_agent : deepagents 库的"装配车间"，把模型+工具组装成 Agent
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent


# ---------- 第 2 步：定义自定义工具（三要素齐全！） ----------
# 三要素 = 课程第2章的核心考点：
#   要素1【清晰功能描述】-> 下面这行 docstring，大模型靠它决定"何时用这个工具"
#   要素2【类型注解参数】-> a: float, b: float，自动生成参数说明书(args schema)
#   要素3【明确返回值】  -> -> float，返回值会包成"工具结果"喂回给大模型
def add(a: float, b: float) -> float:
    """Add two numbers precisely and return the sum."""
    out = a + b                                   # 真正的计算发生在这里（本地！）
    print(f"[TOOL EXEC] add(a={a}, b={b}) -> {out}")  # 打个日志，证明函数真的被执行了
    return out                                    # 返回值 -> 变成 ToolMessage 喂回大模型
# 注：不用写 @tool 装饰器，create_deep_agent 会自动把裸函数包装成工具。


# ---------- 第 3 步：配置大模型 ----------
model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "glm-5.3"),  # 默认智谱 glm-5.3
    api_key=os.environ["OPENAI_API_KEY"],     # 从环境变量取（绝不明文写 Key）
    base_url=os.environ["OPENAI_API_BASE"],   # 智谱的 API 地址
    max_tokens=8192,   # 单次回复上限（glm-5.3 是思考模型，给足空间防止截断）
    timeout=240,       # 思考模型比较慢，超时给 240 秒
)

# ---------- 第 4 步：组装 Agent（一行搞定） ----------
agent = create_deep_agent(
    tools=[add],        # 把我们的函数挂上去（可挂多个：tools=[add, search, ...]）
    model=model,
    system_prompt="You are a precise calculator assistant. Always use the `add` tool for arithmetic instead of computing yourself.",
    # ↑ 系统提示词：告诉大模型"算术必须用 add 工具，别自己心算"
    #   （不强调的话，大模型很可能直接自己算 12345.678+8765.432 然后答错）
)

# ---------- 第 5 步：发起请求 ----------
q = "Please use the add tool to compute 12345.678 + 8765.432, then tell me the result."
print(f"[REQUEST] {q}")
# invoke() = 一次完整的 Agent 循环（可能内部跑很多轮 LLM 调用）
# 入参格式固定：{"messages": [{"role": "user", "content": 问题}]}
result = agent.invoke({"messages": [{"role": "user", "content": q}]})

# ---------- 第 6 步：打印"消息轨迹"（Trace 证据） ----------
# result["messages"] 是整个过程的完整对话历史，每条消息都有 type：
#   human(你的提问) / ai(大模型发言或点工具) / tool(工具执行结果)
print("==== MESSAGE TRACE ====")
log = []
for m in result["messages"]:
    tc = getattr(m, "tool_calls", None)   # ai 消息上才有：它想调用哪些工具
    tcs = [(c["name"], c["args"]) for c in tc] if tc else None  # 提炼成 (工具名, 参数)
    name = str(getattr(m, "name", "") or "")           # tool 消息记录执行了哪个工具
    typ = str(getattr(m, "type", "") or type(m).__name__)
    content = str(m.content)[:100] if m.content else ""  # 文字内容（截断到100字符防刷屏）
    row = {"type": typ, "name": name, "content": content, "tool_calls": tcs}
    log.append(row)
    print(f"- {typ:12s} name={name:6s} content={content!r} tool_calls={tcs}")

# ---------- 第 7 步：把 Trace 存成 JSON（打卡交作业的证据） ----------
with open("/root/ch02_lite/trace.json", "w") as f:
    json.dump(log, f, ensure_ascii=False, indent=1)
print("[SAVED] /root/ch02_lite/trace.json")

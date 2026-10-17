# ============================================================
# 【第3章 Lab3】大结果治理：截断(truncation) vs 卸载(eviction)
# ============================================================
# 源码实证（deepagents 0.7.8, middleware/filesystem.py）：
#   NUM_CHARS_PER_TOKEN = 4
#   tool_token_limit_before_evict = 20000 (默认)
#   → 红线 = 20000 token × 4 字符/token = 80000 字符
#
# 超线后有【两套】机制，分工不同：
#   A) read_file 就地截断：返回内容 > 80K 字符 → 只留前 80K 字符，
#      尾巴上拼一句 "[Output was truncated due to size limits. ...]"
#      文件本身没动，Agent 可以带 offset/limit 分页再读。
#   B) 其它工具(含自定义工具/execute) → 主动卸载(proactive offload)：
#      完整结果写到虚拟磁盘 /large_tool_results/<工具调用id>，
#      原消息替换成提示语 + 头5行/尾5行预览(中间标 [N lines truncated])。
#      提示语原文(TOO_LARGE_TOOL_MSG)：
#        "Tool result too large, the result of this tool call {id} was
#         saved in the filesystem at this path: {path} ...
#         You can read the result ... using the read_file tool,
#         ... offset=0 and limit=100 ..."
#      → Agent 被教得明明白白：按需分页读回，上下文窗口保住了。
#
# 跑法（WSL）：cd /root/ch03_labs && /root/research_deepagent/.venv
# ============================================================
import os, json, functools
print = functools.partial(print, flush=True)

# ---------- 第 0 步：环境（与 lab1 相同的 .env 加载） ----------
def load_env(p):
    for ln in open(p):
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            os.environ.setdefault(k, v.strip())
load_env("/root/research_deepagent/.env")
os.environ.setdefault("AGENTSEEK_MODEL", "deepseek-flash")

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from deepagents import create_deep_agent

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
)

# ---------- 自定义工具：模拟"一次吐出 12 万字符服务器日志" ----------
# 2000 行 × 60 字符 ≈ 120K 字符 ≈ 3 万 token —— 必然超 80K 红线
@tool
def get_server_log() -> str:
    """返回完整的服务器日志（很大）。需要日志内容时调用。"""
    return "\n".join(f"2026-10-15 12:00:{i%60:02d} INFO worker-{i%8} job={i:05d} status=ok bytes={i*37}" for i in range(2000))

agent = create_deep_agent(model=model, tools=[get_server_log])

# ---------- 实验A：read_file 就地截断 ----------
BIG = "\n".join(f"LINE-{i:05d} " + "数据" * 22 for i in range(4000))  # ~40万字符
print(f"预置大文件 big.md：{len(BIG)} 字符（红线 80000）")

# 注意坑：0.7.8 里 files 预置的值必须是 {"content": 字符串}，
# 直接给纯字符串会在 read_file 时炸 TypeError（实测）
# 另一个坑（实测）：read_file 不带 limit 时默认只读 100 行！
# 要触发"就地截断"，必须显式给大 limit（比如 limit=4000）
r = agent.invoke({"messages": [{"role": "user", "content":
    "请用 read_file 读 /workspace/big.md，参数用 offset=0, limit=4000（一次读完4000行），"
    "然后只回答：你实际收到了多少行？内容末尾有没有英文提示说输出因大小限制被截断了？"}],
    "files": {"/workspace/big.md": {"content": BIG}}})

print("\n==== A) read_file 超限 → 就地截断 ====")
truncated = [m for m in r["messages"]
             if m.type == "tool" and "truncated" in str(m.content).lower()]
for m in r["messages"]:
    if m.type == "tool":
        print(f"tool {m.name:14s} 返回 {len(str(m.content)):7d} 字符")
print("截断标记出现:", bool(truncated))
print("Agent 总结:", str(r["messages"][-1].content)[:220])

# ---------- 实验B：自定义工具 → 卸载到虚拟磁盘 ----------
print("\n==== B) get_server_log 超限 → 卸载+预览 ====")
r2 = agent.invoke({"messages": [{"role": "user", "content":
    "调用 get_server_log 拿完整日志，然后告诉我最后一条日志的 job 编号是多少。"}]})

evicted = [m for m in r2["messages"]
           if m.type == "tool" and "Tool result too large" in str(m.content)]
for m in r2["messages"]:
    if m.type == "tool":
        c = str(m.content)
        tag = " ← 被卸载替换!" if "Tool result too large" in c else ""
        print(f"tool {m.name:14s} 返回 {len(c):6d} 字符{tag}")
if evicted:
    print("\n--- 替换后的提示语(前600字符) ---")
    print(str(evicted[0].content)[:600])

print("\n虚拟磁盘里多出来的卸载文件:")
for p, v in (r2.get("files") or {}).items():
    if "large_tool_results" in p:
        n = len(v["content"]) if isinstance(v, dict) and "content" in v else len(v)
        print("  [file]", p, f"({n} chars)")

final = str(r2["messages"][-1].content)
print("\nAgent 最终回答(能答对说明'按需读回'闭环成功):", final[:200])

json.dump({
  "A_truncated": bool(truncated),
  "A_tool_msg_lens": [len(str(m.content)) for m in r["messages"] if m.type == "tool"],
  "B_evicted_msg": str(evicted[0].content)[:800] if evicted else None,
  "B_eviction_files": {p: len(v) for p, v in (r2.get("files") or {}).items()
                       if "large_tool_results" in p},
  "B_final": final[:300],
}, open("lab3_evidence.json", "w"), ensure_ascii=True, indent=1)
print("\n[SAVED] lab3_evidence.json")
ok = bool(truncated) and bool(evicted)
print("DONE" if ok else "PARTIAL")

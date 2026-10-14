# ============================================================
# 【第2章 Basic 级】通过 HTTP 服务调用主项目里的 add 工具
# ============================================================
# 与 Lite 的区别：
#   Lite  = 本地脚本，agent.invoke() 直接在进程里跑
#   Basic = 主项目被 agentseek dev 拉成一个 HTTP 服务(:2024)，
#           我们用 HTTP 请求跟它对话 —— 这才是"服务化"的 Agent
# 前提：先启动服务（见教学指南 STEP 2 的 systemd-run 命令）
# ============================================================
import httpx, json

base = "http://127.0.0.1:2024"   # agentseek dev 服务地址（WSL 内部）

# ---- 第 1 步：建会话线程（thread）----
# thread = 服务端的"记忆本"，同一 thread_id 里的多轮对话互相记得
t = httpx.post(f"{base}/threads", json={}, timeout=30).json()
tid = t["thread_id"]
print("thread:", tid)

# ---- 第 2 步：投递一次运行并等结果 ----
# runs/wait = "跑完再返回"（对应还有 runs/stream 流式版）
q = "Please use ONLY the add tool to compute 12345.678 + 8765.432, then report the result. Do not search the web."
r = httpx.post(
    f"{base}/threads/{tid}/runs/wait",
    json={
        "assistant_id": "research",   # 用主项目的 graph（已挂 add 工具）
        "input": {"messages": [{"role": "user", "content": q}]},
    },
    timeout=580,
)
r.raise_for_status()
state = r.json()

# ---- 第 3 步：解析消息轨迹（和 Lite 的 4 条消息同构）----
print("==== MESSAGE TRACE (via HTTP) ====")
for m in state["messages"]:
    typ = m.get("type", "")
    name = m.get("name") or ""
    content = str(m.get("content", ""))[:100]
    tcs = [(c["name"], c["args"]) for c in (m.get("tool_calls") or [])]
    print(f"- {typ:12s} name={name:6s} content={content!r} tool_calls={tcs}")

json.dump({"thread_id": tid, "messages": state["messages"]},
          open("/root/ch02_lite/basic_trace.json", "w"), ensure_ascii=True, indent=1)
print("[SAVED] /root/ch02_lite/basic_trace.json")
print("DONE" if any(m.get("type") == "tool" and m.get("name") == "add" for m in state["messages"]) else "ADD_TOOL_NOT_CALLED")

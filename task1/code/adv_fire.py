# -*- coding: utf-8 -*-
"""
adv_fire.py — 向 add 工具发射三发"炮弹"（04_Advanced 攻防测试）
=================================================================
对照 04 文档的实验设计：
  ① normal  正常输入（baseline）
  ② empty   空输入（不给数字，看大模型是硬调还是反问）
  ③ huge    超长输入（第二个操作数是 400+ 位天文数字，看它忠实搬运还是心算）

用法（和 run_basic.py 一样走裸 HTTP，正好复习 Basic 级链路）：
  python adv_fire.py            # 三发全打
  python adv_fire.py empty      # 只打某一发
"""
import httpx, json, time, sys

base = "http://127.0.0.1:2024"

FIRES = {
    "normal": "Please use the add tool to compute 12345.678 + 8765.432. Do not search the web.",
    "empty":  "Please use the add tool to compute the sum. Do not search the web.",   # 没给数字
    "huge":   "Please use the add tool to compute 12345.678 + " + "9" * 400 + ". Do not search the web.",
}

def fire(tag: str, q: str):
    print("=" * 60)
    print(f"[{tag}] 炮弹装填: {q[:80]}{'...' if len(q) > 80 else ''}")
    t0 = time.time()
    tid = httpx.post(f"{base}/threads", json={}, timeout=30).json()["thread_id"]
    r = httpx.post(
        f"{base}/threads/{tid}/runs/wait",
        json={"assistant_id": "research",
              "input": {"messages": [{"role": "user", "content": q}]}},
        timeout=580,
    )
    r.raise_for_status()
    msgs = r.json()["messages"]
    print(f"  thread={tid}  消息数={len(msgs)}")
    n = 0
    for m in msgs:
        typ, name = m.get("type", ""), m.get("name") or ""
        if n == 0 and typ != "human":      # 跳过历史残留只打新增（新 thread 其实全新增）
            continue
        n += 1
        if typ == "ai" and m.get("tool_calls"):
            for c in m["tool_calls"]:
                print(f"  >> 点单: {c['name']}{json.dumps(c['args'], ensure_ascii=False)[:120]}")
        elif typ == "tool":
            print(f"  << 返回: {name} = {str(m.get('content'))[:120]}")
        elif typ == "ai":
            c = str(m.get("content", ""))
            if c.strip():
                print(f"  ## 回答: {c[:150]}")
    json.dump({"fire": tag, "q": q, "thread_id": tid, "messages": msgs},
              open(f"/root/ch02_lite/adv_{tag}.json", "w"), ensure_ascii=True, indent=1)
    print(f"  耗时 {time.time() - t0:.1f}s → 存 /root/ch02_lite/adv_{tag}.json")

if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for tag, q in FIRES.items():
        if only and tag != only:
            continue
        try:
            fire(tag, q)
        except Exception as e:
            print(f"[{tag}] 炸膛: {type(e).__name__}: {e}")
    print("\n三发完毕 — 去 LangSmith 看 trace 树，对照 04 文档回填表格。")

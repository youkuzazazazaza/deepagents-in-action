# ============================================================
# 【第3章 Lab4】FilesystemPermission：给文件上锁
# ============================================================
# 一句话：权限规则 =（操作、路径、模式）三元组，先匹配先生效。
#   allow  = 放行      deny = 直接拒绝（工具返回错误文字，Agent 看得到）
#   interrupt = 暂停等人拍板（Human-in-the-Loop 预告篇，第9章细讲）
#
# 实验设计：
#   1) deny 写 /secret/**  → Agent 想写被拒 → 只好改写到 /workspace/
#   2) interrupt 读写 /vault/** → 图直接暂停（interrupt）→ 人说"同意"再继续
#
# 跑法（WSL）：
#   cd /root/ch03_labs && /root/research_deepagent/.venv/bin/python \
#       /mnt/d/gitcode/learn/deepagents-in-action/task2_ch03/code/lab4_permissions.py
# ============================================================
import os, json

def load_env(p):
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env("/root/research_deepagent/.env")

from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent, FilesystemPermission

model = ChatOpenAI(
    model=os.environ.get("AGENTSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"],
    max_retries=2,
)

# ---------- 第 1 步：deny /secret/** ----------
agent = create_deep_agent(
    model=model,
    permissions=[
        FilesystemPermission(
            operations=["write", "read"],   # 管哪些操作：读/写
            paths=["/secret/**"],            # 管哪些路径：secret 目录下所有
            mode="deny",                     # 模式：拒绝
        )
    ],
)
r1 = agent.invoke({"messages": [{"role": "user", "content":
    "请把内容 '内幕情报' 写入 /secret/plan.md，写入成功后 read_file 读回确认。"
    "如果被拒绝，就改写入 /workspace/plan.md 并告诉我你最终写到了哪里。"}]})

print("==== 实验1：deny /secret/** ====")
for m in r1["messages"]:
    c = str(m.content).replace("\n", " ")
    flag = " <<< 被拒" if "denied" in c.lower() or "拒绝" in c else ""
    print(f"- {m.type:10s} {m.name or '':12s} {c[:110]!r}{flag}")

final1 = str(r1["messages"][-1].content)
print("\n最终回答:", final1[:300])

# ---------- 第 2 步：interrupt /vault/**（人拍板） ----------
agent2 = create_deep_agent(
    model=model,
    permissions=[
        FilesystemPermission(
            operations=["write", "read"],
            paths=["/vault/**"],
            mode="interrupt",     # 碰到就暂停，等人决定
        )
    ],
)
r2 = agent2.invoke({"messages": [{"role": "user", "content":
    "请把内容 '金库密码' 写入 /vault/password.txt。"}]})

print("\n==== 实验2：interrupt /vault/** ====")
# 图被暂停时 __interrupt__ 出现在结果里，messages 停在"想写但没写成"那一刻
print("结果 keys:", list(r2.keys()))
interrupts = r2.get("__interrupt__") or []
for it in interrupts:
    print(f"[INTERRUPT] value={getattr(it, 'value', it)!s:.300}")

if interrupts:
    # 人拍板：同意 → 用 Command 恢复运行
    from langgraph.types import Command
    r2b = agent2.invoke(Command(resume="approve"), config=r2["__config__"]) \
        if "__config__" in r2 else None
    if r2b is None:
        # 老版本用 thread config 兜底：直接重新 invoke 不可取，教学上打印说明即可
        print("(恢复需要 checkpointer 保存现场；本地临时图参考教学指南 STEP 4 的完整版)")
    else:
        print("恢复后最终回答:", str(r2b["messages"][-1].content)[:200])

json.dump({"final1": final1[:400],
           "had_interrupt": bool(interrupts)},
          open("lab4_evidence.json", "w"), ensure_ascii=True, indent=1)
print("\n[SAVED] lab4_evidence.json")

# 03 · LangSmith：零代码给 Agent 装"后厨监控"

> 前置：02 的 HTTP 服务已跑通。本文所有配置**只动 .env，一行代码都不改**。
> ⚠️ Key 安全：真实 key 只存 WSL 的 `/root/research_deepagent/.env`，绝不进本仓库（文档一律打码 `lsv2_pt_***`）。

---

## 一、LangSmith 是什么？

LangSmith = LangChain 官方的**云端观测平台**。Agent 每跑一次，它把完整过程（LLM 每步在想什么、何时调工具、工具输入输出、耗时、token 花销）自动画成一棵 **trace 树**上传云端。你打开 [smith.langchain.com](https://smith.langchain.com) 就能逐帧回放。

**为什么值得开**：第二章作业的"Trace 证据"、第三章以后的调试，全靠它——没有观测的 Agent 开发等于闭眼开车。

## 二、接入：只加 3 行环境变量（零代码！）

在 WSL 里编辑 `/root/research_deepagent/.env`，追加：

```ini
LANGSMITH_API_KEY=lsv2_pt_***        # 你的 key（smith.langchain.com → Settings → API Keys）
LANGSMITH_TRACING=true              # 总开关：开=每次运行自动上报
LANGCHAIN_TRACING_V2=true           # 旧版变量名，兼容写法，一起开保险
```

然后**必须重启服务**（原因见 4.1）：

```bash
systemctl stop agentdev 2>/dev/null; bash /root/ch02_lite/start_dev.sh &
```

## 三、为什么一行代码都不用写？（设计精髓）

grep 整个 `src/` 目录：**零处** `LANGSMITH` 引用。生效靠三段自动接力：

```
agent.py:30   load_dotenv()                    ← 唯一的钩子：把 .env 搬进进程环境变量
                     ↓
langchain 库 import 时: 自动检查 LANGSMITH_TRACING / LANGSMITH_API_KEY
                     ↓ 发现存在 → 自动开启上报
每次运行:    LLM调用、工具执行 → 异步批量 → LangSmith 云端
```

**为什么这么设计？** 观测是"横切关注点"（cross-cutting concern），若接入要改业务代码，观测和逻辑就耦合了。环境变量开关 = **插拔式观测**：哪天不想用，删两行、重启，代码零改动。日志/监控/tracing 都是这个套路。

## 四、两个真实坑（我踩的，都是教材）

### 4.1 改了 .env 必须重启服务——伏笔回收

服务进程的环境变量是**启动那一刻的快照**。`load_dotenv()` 只在 agent.py 被 import 时执行一次。改完 .env 不重启，跑一万次 trace 也不会上报——运行中的进程根本不知道 .env 变了。**配置文件 ≠ 数据库，它不是实时读的。**

### 4.2 /proc/PID/environ 的快照陷阱（进阶）

想验证"服务进程拿到 key 没有"，去读 `/proc/<pid>/environ`——**空的**！差点误判。真相：`/proc/environ` 显示的是 **execve 启动瞬间**的环境，而 `load_dotenv()` 改的是进程**内存里**的 `os.environ`，永远不会回写 /proc。

> 教训：**验证"运行时状态"要用运行时的行为去实证**（比如调 LangSmith 云端 API 查有没有新 run），而不是看静态快照。

## 五、验证闭环（我是这样实证的）

```bash
# 1) 跑一次
cd /root/ch02_lite && python run_basic.py

# 2) 直接问 LangSmith 云端："刚才有 run 上来吗？"
curl -s -H "x-api-key: lsv2_pt_***" \
  "https://api.smith.langchain.com/api/v1/sessions?limit=5"
```

云端应答（节选）——`last_run_start_time` 和我跑的时刻分秒吻合，铁证：

```json
{"name": "default",
 "last_run_start_time": "2026-10-14T14:26:37Z",
 "trace_tier": "shortlived"}
```

> `default` 是没设 `LANGCHAIN_PROJECT` 时的默认项目名。想分项目隔离，可在 .env 加 `LANGCHAIN_PROJECT=deepagents-ch02`。

## 六、动手与观察

1. 打开 https://smith.langchain.com → 左侧 **Projects → default**
2. 点开最新 run，看 trace 树：
   - **LLM 节点**：模型每轮的输入输出、思考过程、token 数、耗时
   - **tool 节点**：`add` 的入参 `{a, b}` 和返回 `21111.11`
3. 对照 02 的 4 条消息——树上的节点就是它们的展开版

## 七、自测 2 题

1. 删掉 `LANGSMITH_TRACING=true` 这行后（不重启），trace 还传吗？重启后呢？
2. 为什么 LangSmith 能知道 `add` 工具的输入输出，而 `add` 函数里没写任何上报代码？

<details>
<summary>参考答案</summary>

1. 不重启：照传（进程内存里的环境变量还在）；重启后：停（新快照里没有这个开关了）。
2. 上报逻辑在 langchain 运行时里——它包裹（wrap）了 LLM 调用和工具执行的入口，从外面看进去，而不是要每个函数自己写。
</details>

---

## 下一关预告

**04 · Advanced**：向 `add` 工具发射两发"炮弹"——空输入、超长输入，看 Agent 的防御姿势，并用 LangSmith 留下 Trace 证据（冲优秀作业的关键素材）。

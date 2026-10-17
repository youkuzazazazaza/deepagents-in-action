# 第3章作业打卡 · 学有余力：State / Filesystem / Store 三角对比

**验证什么**
补上第三种后端 StoreBackend（LangGraph BaseStore 键值库），做三角对照：
- 角1 State：换一次 invoke，文件没了？
- 角2 Filesystem：换一个全新 Agent 实例，文件还在？
- 角3 Store：换实例还在？换一个**全新的 store 实例**呢？

**怎么做的（改了什么）**
代码 `code/hw_bonus_store.py`。接线：`StoreBackend(namespace=lambda rt: ("ch03", "files"), store=InMemoryStore())` 直接在构造时把 store 传进去；三角用同一条任务指令写 `/workspace/tri.md`，再各自用"最坏情况"去读。另用 `store.search(("ch03","files"))` 直接透视库内部。

**实际结果（四项判定全部 True）**
```
state_lost_without_files:    True   ← State 新 invoke：read 报 not found
fs_survives_new_instance:    True   ← FS 新实例：读回「三角对比实验数据」
store_survives_new_instance: True   ← Store 新实例（同一个 store）：读回原文
store_dies_with_new_store:   True   ← 换全新 InMemoryStore：not found
```
透视记录（store.search 返回）显示文件以 key=`/workspace/tri.md` 存进命名空间，value 结构含 `content / encoding / created_at / modified_at`——Store 里存的其实是**带元数据的文件对象**，不是裸文本。

**证据与解释**
`evidence/hw_bonus_evidence.json` 四项 verdict + `store_search_internal` 原始记录。三角总结（生命周期各跟谁走）：

| 后端 | 文件真实住处 | 生死跟谁走 | 一句话 |
|---|---|---|---|
| State | Agent State（state["files"]） | 一次 invoke | 草稿本，交卷即焚 |
| Filesystem | root_dir 磁盘 | 磁盘目录 | 真房子，人走家还在 |
| Store | BaseStore 命名空间 | store 实例 | 仓库，换库全丢、接 Postgres 则可跨进程持久 |

**下一步修正**
InMemoryStore 演示的是"Store 的生死 = store 实例"这一面；生产上接 LangGraph 的 PostgresStore 才是它的完全体（跨进程、可检索）。另外本三角只测了"在/不在"，Store 的按 namespace 检索能力（search 向量召回）值得单独再开一lab。

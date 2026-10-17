# 第3章作业打卡 · Basic 基础级：路径与后端的关系

**验证什么**
同一批虚拟路径 `/workspace/资料/…`、`/workspace/报告/…`，Agent A（root_dir=basic_a）写、改，Agent B（root_dir=basic_b）去读——验证"**路径是虚拟的，家（Backend 的 root_dir）决定文件真实住哪**"。

**怎么做的（改了什么）**
- 代码：`code/hw_basic.py`
- A 三轮：写 research.md（故意埋错："大结果会自动卸载到文件"那条写漏了半句）→ 读回 → 修正错句并让 Agent 基于资料写 report.md
- B 一轮：不指定任何 root_dir 关系，直接读 A 的文件路径

**实际结果**
- A 侧：research.md 错句已被 Agent 补成"大结果会自动卸载到文件，对话历史会自动总结"，报告含三条"结论N:"编号行，均落盘在 `basic_a/workspace/资料/` 与 `basic_a/workspace/报告/`（见 evidence `disk_a_files`）
- B 侧（最有教学价值的一段）：B 如实报告任务失败——
  > `ls /workspace` → `Error: Path '/workspace': path_not_found`，`read_file /workspace/资料/research.md` → `not found`，连 `/tmp`、`/home` 都探测了一遍，最后老实承认"文件读不到，任务未能完成"

**证据与解释**
`evidence/hw_basic_evidence.json`：`disk_a_files` 证明文件只存在于 A 的 root_dir 下；`b_final` 是 B 的失败自述原文。解释：文件系统后端之间互相隔离，路径相同 ≠ 看到同一批文件，root_dir 才是"家"的坐标。B 没有幻觉编造内容而是如实报错，也侧面说明工具层错误信息够诚实。

**下一步修正**
B 的失败是"换家读不到"，但还没对比"同一个家、换了住户（Agent 新实例）读不读得到"，以及 State 后端两轮 invoke 之间的生死——交给 Advanced。

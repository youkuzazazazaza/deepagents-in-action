# 第3章作业打卡 · Advanced 挑战级：生命周期对比 + 覆盖差异，全程可复现

**验证什么**
两组对照实验，五项独立判定：
- A 生命周期：StateBackend 第2轮 invoke 文件是否消失；FilesystemBackend 换**全新 Agent 实例**能否读回；把磁盘目录改名后旧实例是否立刻失明
- B 覆盖差异：write_file 覆盖同名文件，旧版本是否就地蒸发；State 里的旧版本快照能否作为"后悔药"

**怎么做的（改了什么）**
代码 `code/hw_advanced.py`，每个结论都有独立证据行；覆盖实验用两次磁盘内容做 sha256 前 12 位留档，而不是口头说"变了"。

**实际结果（五项判定全部 True）**
```
state_round2_lost:          True   ← State 第2轮 ls /workspace = No files found
fs_new_instance_ok:         True   ← 全新 FS 实例读回 life.md 原文「草稿B」
fs_dies_with_disk:          True   ← 磁盘目录改名后，FS 实例读文件报 not found
state_snapshot_rescue:      True   ← 把第1轮 state["files"] 塞回第2轮，读回「版本一」
fs_overwrite_destroys_v1:   True   ← 覆盖后磁盘 hash 938c10bcbaf8 → d5e92dd2d5ea
```
最有意思的一条：State 的"短命"不全是缺点——覆盖实验里 StateBackend 的 state 快照还留着被覆盖的「版本一」原文（版本的可挽回性），而 FilesystemBackend 磁盘上旧版本已被就地销毁，hash 就是铁证。

**证据与解释**
`evidence/hw_advanced_evidence.json`：A3 磁盘文件路径 `/root/ch03_hw/adv_fs/workspace/life.md`；B2 行给出两个 hash；`verdict` 五项布尔值。生命周期一句话总结：**State 活在一次 invoke 里，FS 活在 root_dir 里**——一个跟人走，一个跟家走。

**下一步修正**
覆盖丢版本说明"想留版本就得换能带历史的后端"——Store 是不是那块拼图？交给 Bonus 三角对比验证。

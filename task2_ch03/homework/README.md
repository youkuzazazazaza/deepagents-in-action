# 第3章作业包：State / Filesystem / Store 后端实战

三个难度档 + 学有余力，全部真机跑通（WSL Ubuntu + deepseek-flash，deepagents 0.7.x），证据全部落盘可复现。

## 目录
```
code/    hw_lite.py        打卡级：写入—读回—修改，磁盘亲手验货
         hw_basic.py       基础级：A写B读，路径是虚拟的、家(root_dir)才是坐标
         hw_advanced.py    挑战级：State vs FS 生命周期五判定 + 覆盖hash取证
         hw_bonus_store.py 学有余力：三后端三角对比（含 store 内部透视）
notes/   hw_lite_daka.md 等 4 份打卡笔记（验证什么/怎么做的/实际结果/证据与解释/下一步）
         hw_lite_teach.md 等 4 份教学详解（完整代码全注释 + 大白话逐段拆解 + 真实输出摘录 + 踩坑 + 一句话记住）
evidence/ 4 份 *_evidence.json + lite 磁盘产物副本 lite_proj/
```

## 一键复现（WSL）
```bash
mkdir -p /root/ch03_hw && cd /root/ch03_hw
V=/root/research_deepagent/.venv/bin/python
for s in hw_lite hw_basic hw_advanced hw_bonus_store; do
  $V /mnt/d/gitcode/learn/deepagents-in-action/task2_ch03/homework/code/$s.py
done
# 每个脚本末尾打印 DONE（或逐项判定 True）即通过；证据 json 生成在当前目录
```

## 踩坑提醒（本包实测）
- `FilesystemBackend(root_dir=…, virtual_mode=True)` 下 `/workspace/xxx` 落盘在 **root_dir/workspace/xxx**，挂载点名会保留，别去 root_dir/xxx 下找
- StoreBackend 构造签名是 `namespace: Callable[[Runtime], tuple]` + `store: BaseStore`，InMemoryStore 可直接传入；namespace 是"分格抽屉"
- 修改任务建议埋真错误（错日期/漏半句），Agent 的修改才有实事可做，验证也才有分辨力

## 三角结论速查
| 后端 | 文件住处 | 生死跟谁 | 一句话 |
|---|---|---|---|
| State | state["files"] | 一次 invoke | 草稿本，交卷即焚 |
| Filesystem | root_dir 磁盘 | 磁盘目录 | 真房子，人走家还在 |
| Store | BaseStore 命名空间 | store 实例 | 仓库，接 Postgres 跨进程 |

关联正文实验：`../labs/`（lab1 StateBackend 草稿本、lab2 FilesystemBackend 落盘与虚拟路径）。

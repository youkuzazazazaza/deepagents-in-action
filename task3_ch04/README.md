# 第4章 · 规划与上下文工程（TodoList / Summarization / Patch）实战包

> 原书第4章配套学习材料。**所有结论基于 deepagents 0.7.8 + langchain 1.4.3 真机实测**，
> 与书中描述有出入处已在 notes 里特别标注（版本演进，以实测为准）。

## 学习路径（建议顺序）

1. `notes/01_本章地图.md` —— 先建立全景：中间件是什么、本章四问
2. `notes/02_lab1_中间件改图.md` —— TodoList 如何改图、三状态生命周期
3. `notes/03_lab2_记忆与存档.md` —— Checkpointer / thread_id，失忆 vs 读档
4. `notes/04_lab3_摘要与归档.md` —— 摘要三参数 + 0.7.8 两大版本坑（★本章最难也最有料）
5. `notes/05_lab4_保险丝与全景.md` —— 悬空 tool_call 400 报错与自愈，五配置全景表
6. `notes/06_避坑清单.md` —— 七个实测坑 + 一页速查表

## 目录

```
task3_ch04/
├── code/        lab1~lab4 四个可独立复跑的实验脚本（WSL python 3.12 + .env 的 DEEPSEEK key）
├── evidence/    每个实验的完整原始输出（txt + json），笔记里每条结论都能在这里找到原文
├── notes/       六篇超详细大白话笔记（本目录即课件正文）
└── assets/      四张教学图（svg + png）
    d1 计划驱动的工作流（三状态流转）
    d2 两类中间件 Hook：改图节点 vs 包裹模型调用
    d3 摘要与归档流水线（含 KeyError 'files' 罢工现场）
    d4 中间件全景：全家桶 vs 自选组装
```

## 复跑方式

```bash
cd code
python lab1_todo_lifecycle.py        # 依赖 .env 里的模型 key（deepseek-flash）
python lab2_todo_persistence.py
python lab3_summarization_anchor.py  # 约 3-5 分钟
python lab4_patch_and_panorama.py
```

## 一句话总结本章

**计划外置（TodoList）+ 记忆存档（Checkpointer）+ 历史压缩（Summarization+Filesystem）+ 崩溃自愈（PatchToolCalls）**——四件装备凑齐，Agent 才配得上"深任务"三个字。`create_deep_agent()` 全家桶默认配齐；自己组装时，坑 1~坑 4（见 06）正等着你。

## 配图（assets/，SVG 可编辑源 + PNG + 质检全过）

| 文件 | 用在哪 | 说明 |
|---|---|---|
| d1_plan_workflow | notes/02 | 计划驱动工作流主循环 |
| d2_two_hooks | notes/02 | 改图型 vs 包裹型两类中间件 |
| d3_summarization_pipeline | notes/04 | 摘要三参数 + 归档管线（含 files 坑） |
| d4_panorama | notes/05 | 全家桶 vs 自选组装 + 四坑速查 |

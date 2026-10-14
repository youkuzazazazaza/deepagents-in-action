# Task 1 · 第二章 Deep Agents 快速上手（教学档案）

> 对应教程：https://datawhalechina.github.io/deepagents-in-action/chapters/ch02-quickstart/
> 打卡目标：跑通自己的第一个 Deep Agent，说清「请求 → 执行 → 返回」；进阶：空/超长输入对比 + Trace 证据 + 双模型对比。

## 📁 目录导读

| 文件 | 内容 | 状态 |
|---|---|---|
| `notes/01_Lite_第一个DeepAgent.md` | 打卡级：Lite 架构、工具三要素、args schema、逐行讲解 | ✅ 已跑通 |
| `notes/02_Basic_HTTP架构.md` | 常驻服务架构、thread 机制、graph 命名坑、add 接线全链 | ✅ 已跑通 |
| `notes/03_LangSmith观测.md` | 零代码接入 tracing、云端实证、/proc 陷阱、快照伏笔 | ✅ 已配置 |
| `notes/04_Advanced_攻防测试.md` | 冲优秀：空/超长输入三发炮弹实测✅（huge 触发服务端自救 27 条消息名场面） | ✅ 实测 |
| `notes/05_双模型对撞.md` | 学有余力：glm-5.3 ↔ deepseek-flash 换脑实操（切模型步骤+坑+对照表） | 🔄 normal已撞完 |
| `notes/06_打卡心得.md` | 四条大白话打卡心得（Basic=四件套对应代码展开版）+ Trace 导出指南 | ✅ 可直接抄 |
| `code/lite_agent.py` | Lite 参考实现（小白注释版，可直接读） | ✅ |
| `code/run_basic.py` | HTTP 客户端脚本（Basic 打卡用） | ✅ |
| `code/start_dev.sh` | 服务自救脚本（WSL 关机后拉起 agentseek dev） | ✅ |
| `assets/basic_agent_arch.svg/.png` | 🖼️ Basic 级全链路架构图（PNG 可直接看，JSON 可编辑重渲染） | ✅ |


![Basic Deep Agent over HTTP](assets/basic_agent_arch.png)

## 🚀 三分钟复现（WSL Ubuntu 内）

```bash
# 0) 服务没起就先拉起（Connection refused 时执行）
bash /root/ch02_lite/start_dev.sh &

# 1) Lite 级：进程内 Agent
cd /root/ch02_lite && python lite_agent.py

# 2) Basic 级：HTTP 常驻服务
python run_basic.py && cat basic_trace.json
```

## 🗺️ 学习路线（当前进度）

```
[✅] Step 1 Lite    —— 脚本进程里的 Agent（一次性厨师）
[✅] Step 2 Basic   —— HTTP 常驻服务（开餐厅）
[✅] Step 2.5 LangSmith —— 云端观测（后厨监控）
[✅] Step 3 Advanced —— 空/超长输入炮弹 + Trace 取证（两轮复测完成）
[🔄] Step 4 双模型   —— glm-5.3 vs deepseek-flash：normal 已撞完（DS 快 2.7 倍、双满分），empty/huge 待亲手补
```

## ⚠️ 安全红线

本目录是**公开仓库**，会提交到 GitHub：

- **任何 API Key / .env 内容绝不放进本目录**（真实配置只存在于 WSL 的 `/root/research_deepagent/.env`）
- 文档中出现的 key 一律打码为 `lsv2_pt_***`
- 已放 `.gitignore` 保险丝（`.env*`、`*.log`），防手滑

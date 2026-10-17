# 第3章作业打卡 · Lite 打卡级：写入 — 读回 — 修改

**验证什么**
用三轮 invoke 完成最小闭环：① write_file 原样写入含错日期的会议纪要 → ② 新 invoke 里 read_file 读回 → ③ 修改两处（改日期 + 追加一行）并读回确认。打卡的真正门槛在最后一步：绕开 Agent，亲手在项目目录里找到那份产物。

**怎么做的（改了什么）**
- 代码：`code/hw_lite.py`，FilesystemBackend(root_dir=lite_proj, virtual_mode=True)
- 第一轮我故意在纪要里埋了个错日期 `2026-10-11`（当天实际是 10-17），让第三轮的"修改"有真实事可做，而不是走过场
- 踩坑修正：virtual_mode=True 时 `/workspace/meeting.md` 实际落盘在 `ROOT/workspace/meeting.md`——虚拟路径的挂载点名 `/workspace` 被原样保留在目录结构里，第一版脚本去 `ROOT/meeting.md` 找直接 FileNotFoundError

**实际结果（磁盘原文，非 Agent 转述）**
```
/root/ch03_hw/lite_proj/workspace/meeting.md
# 周会纪要
- 下次例会时间 2026-10-18 上午十点    ← 日期已从 10-11 改对
- 负责人 小王
- 纪要归档 会议纪要目录              ← 新追加的一行
```
第二轮读回时 Agent 还原样报出了错日期（10-11），说明写读链路无污染；第三轮修改后 Agent 主动 re-read 确认了两处变更。

**证据与解释**
`evidence/hw_lite_evidence.json`：`check.date_fixed=true, check.line_appended=true`；`disk_meeting_md` 字段是脚本用 open() 直读磁盘的原文，与 Agent 最终自述逐字一致。磁盘产物副本在 `evidence/lite_proj/`。

**下一步修正**
Lite 级只验证了"文件在"，没验证"文件什么时候不在"——这正是 Basic/Advanced 要补的生命周期视角。

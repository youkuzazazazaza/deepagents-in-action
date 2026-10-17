# 03-02 真磁盘与分区挂载：FilesystemBackend / CompositeBackend

> 对应实验：`code/lab2_filesystem_backend.py` ｜ 证据：`evidence/lab2_out.txt`、`evidence/lab2_evidence.json`

## 一、人话开场：从"草稿纸"升级到"档案柜"

03-01 的 StateBackend 是草稿纸——进程一关就没了。但真实需求常常是：

- **多轮会话接力**：今天聊一半，明天接着来，文件得还在；
- **多 Agent 协作**：两个 Agent 实例要看到同一份文件；
- **产物交付**：Agent 写的报告，人类要用真文件去打开。

这时就该上 **FilesystemBackend**——把虚拟路径直接映射到你硬盘上的一个真实目录：

```python
backend = FilesystemBackend(root_dir="/root/ch03_labs/fsroot")
```

之后 Agent 眼里的 `/workspace/report.md` = 你磁盘上的 `/root/ch03_labs/fsroot/workspace/report.md`。**同一块盘，谁挂谁看见**。

## 二、Lab2 三连实验设计

**A 段：真落盘验证**
Agent A 写 `/workspace/report.md` → 进程结束后，用系统的 `ls -la` 直接看磁盘——绕开 Agent，人肉验证。

**B 段：跨实例共享**
起一个全新的 Agent B（同一个 root_dir），让它读 `/workspace/report.md`。A 写的文件 B 能读到 = 共享成立。

**C 段：CompositeBackend 分区挂载**
一块"拼装盘"：`/shared/**` 挂真磁盘（跨会话共享），`/workspace/**` 和其它留在内存（临时草稿）。

```python
composite = CompositeBackend(
    backends=[fs_shared, StateBackend()],          # default 排最后
    routes=[("/shared", fs_shared)],               # ★ 注意：键是前缀，不是 glob！
)
```

## 三、实测结果（证据摘录）

**A 段——磁盘真相：**

```text
---- 磁盘真相（ls -la /root/ch03_labs/fsroot）----
drwxr-xr-x workspace        ← 真目录真的出现了
```

**B 段——全新实例读到了别人写的文件：**

```text
B 的最终回答: `/workspace/report.md` 的全部内容（共 2 行）：
# 第3章实验
文件真的落盘了吗？
```

**C 段——分区效果（lab2_evidence.json）：**

```json
{
 "disk_root": ["/root/ch03_labs/fsroot/workspace/report.md"],
 "disk_shared": ["/root/ch03_labs/shared/notes.md"],
 "Agent C 的 files": ["/workspace/draft.md"]
}
```

解读：`/shared/notes.md` 在磁盘上躺着（跨会话可见）；`/workspace/draft.md` 只存在于 C 的内存快照里（进程关了就没）。**一块盘，两种命运，全看你挂在哪。**

## 四、⚠️ 本章头号大坑：routes 的键是"前缀匹配"，不是 glob！

**血泪实录**：我第一版 lab2 写的是 `routes=[("/shared/**", fs_shared)]`（想着 glob 语法嘛）。
结果：`/shared/notes.md` 静悄悄地**写进了 default 后端（内存）**，磁盘上啥也没有。**没有任何报错！**

为什么？翻源码（`backends/composite.py`）：

```python
def _resolve_backend(self, path: str) -> BackendProtocol:
    for prefix, backend in self._routes:
        if path.startswith(prefix):   # ← 就是 startswith！
            return backend
    return self._default
```

- `/shared/notes.md`.startswith(`/shared/**`) → **False**（路径里可没有字面量的 `**`）
- → 兜底落 default → 你的"真磁盘分区"被无声绕过

**正确写法与对照**：

| 场景 | 写法 | 匹配方式 |
|---|---|---|
| CompositeBackend routes | `("/shared", backend)` | **前缀** startswith |
| FilesystemPermission path | `"/secret/**"` | **glob**（fnmatch 系） |

同一个包里两套匹配语义并存，这是最容易被面试官（和坑）盯上的细节。**记住：挂载认前缀，权限认通配。**

## 五、三种后端选型速查

| | StateBackend | FilesystemBackend | CompositeBackend |
|---|---|---|---|
| 存储 | LangGraph state（内存） | 真实目录 | 按 route 分发 |
| 进程重启 | 蒸发 | 保留 | 分区各异 |
| 多实例共享 | ❌（除非传 files 快照） | ✅ 天然 | 看挂在哪 |
| 典型用途 | 测试/无痕沙箱/子Agent隔离 | 交付物/长任务 | 混合：共享区+草稿区 |

选型口诀：**要留痕上 FS，要隔离用 State，既要又要就 Composite。**

## 六、自查清单

- [ ] 能口述 A/B/C 三段各自证明了什么
- [ ] 说出 routes 前缀坑的根因（startswith）与症状（静默落 default，零报错）
- [ ] 知道 FilesystemBackend 的 root_dir 是"根替换"：虚拟 `/x` = 磁盘 `root_dir/x`
- [ ] 会画三种后端的选型决策小抄（见 assets 图 2）

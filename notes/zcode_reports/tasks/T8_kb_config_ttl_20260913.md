# T8 · kb_config.json 强制复核机制（对应 D7）· 2026-09-13

## ① 目标与结论

给 KB ID 配置加「超龄强制复核」。**结论：核心机制（verified_at 超龄 → 拒绝上传）已由 9/12 审计轮实现且比任务书建议更严（上限 7 天，非 30 天）；本轮真正的增量 = `confidence` 字段升级为带 TTL 的结构 + 新鲜度闸门自测 5/5 PASS + `--check-integrity` 回归通过。**

## ② 现状复核（kb_uploader.py 实测）

- `_load_kb_id()`（L57-112）：config 缺失/损坏 → 退出；`verified_at` 不可解析 → 拒绝；距今 > `MAX_KB_ID_AGE_DAYS`（= **7 天**，L54）→ 拒绝并提示处置；环境变量 `IMA_KB_ID_AGENT_ROADMAP` 视为已人工实测、跳过闸门（既定设计）。闸门在 **import 时即执行**（`KNOWLEDGE_BASE_ID = _load_kb_id()`）。
- 任务书建议 N=30 天 → 现有 7 天**更严格，保留不改**。

## ③ 本轮增量

1. `tools/kb_config.json` 的 `confidence` 由纯字符串改为 **TTL 结构**（`{level, verified_at, ttl_days: 7, note}`），与脚本上限对齐；`verified_at` 顶层字段保持原样（脚本消费方）。经 grep 确认 `.py` 中无其他 `confidence` 消费方，重构安全。
2. 新增自测 `tools/_test_kb_gate.py`（monkeypatch `__file__` 指向临时目录的 doctored 配置，不触碰真实配置）。

## ④ 实际执行（原始输出）

**配置编辑**（mem_edit，json → 旁挂 version.json）：
```
OK 替换 1 处 | 备份 D:\...\backup\mem-edit\20260913T035115\projects\agent-learning\tools\kb_config.json | 新 sha256 f215d62daacbd978
```

**自测 5/5 PASS**：
```
[PASS] ①真实配置过闸(1天龄) lEJxwm6JaTQ-X6yA-rp4...
[PASS] ②超龄拒绝 KB ID 已 61 天未复核（verified_at=2026-07-14 旧值，上限 7 天）→ 拒绝执行…
[PASS] ③不可解析拒绝 kb_config.json 缺少可解析的 verified_at → 拒绝执行…
[PASS] ④新鲜通过 lEJxwm6JaTQ-X6yA-rp4...
[PASS] ⑤env旁路(既定设计) ENVTESTID=
===== 自测结果: 5/5 PASS =====（退出码 0）
```

**回归**：`kb_uploader.py --check-integrity` 正常执行（57 个文件完整性检查，退出码 0）——配置结构变更未破坏主流程。

## ⑤ 产出物清单

- `tools/kb_config.json`（confidence → TTL 结构；自动备份 `backup\mem-edit\20260913T035115\` + `backup\zcode-20260913\T8\kb_config.json.before`）
- `tools/_test_kb_gate.py`（闸门自测）
- `tools/kb_config.json.version.json`（mem_edit 旁挂版本标记）
- MEMORY_ISSUES.md D7 状态已更新（🟡）

## ⑥ 遗留 / 阻塞

- `folder_ids_verified: false`（FOLDER_MAP 的 folder_id 未复核）仍为 false——属任务书 T8 范围外的既有标注，维持原样，使用前须实测（脚本已有提醒）。

# Open Tasks

## Priority Queue
- [x] P1: 完成 `option_chain_builder.py` 结构瘦身并保持单文件 <= 450 LOC。
  - Owner: Codex
  - Definition of Done: 主编排文件满足长度上限且 helper 外提完成。
  - Blocking: 无。
- [x] P1: 完成 helper 外提（OI preload / REST update / SHM read）并保持行为合同不变。
  - Owner: Codex
  - Definition of Done: 新增 support 模块并由 builder 调用，无回调合同漂移。
  - Blocking: 无。
- [ ] P1: 修复主机 `WinError 10106` 后补跑 bloat 子提案相关 pytest。
  - Owner: Codex
  - Definition of Done: `scripts/test/run_pytest.ps1` 可完成采集并执行目标用例。
  - Blocking: 主机 Python `asyncio` 初始化失败（环境问题，继承自上一会话）。

## Parking Lot
- [ ] P2: 第三子提案继续拆分 `l2_decision/feature_store/extractors.py`。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] `option_chain_builder` bloat split 第二批次完成（2026-03-17 13:16 ET）

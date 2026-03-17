# Open Tasks

## Priority Queue
- [x] P1: 将 `extractors.py` 拆分为主题模块并保留 registry 合同稳定。
  - Owner: Codex
  - Definition of Done: `build_default_extractors` 与 `reset_all_default_extractors` 行为保持一致。
  - Blocking: 无。
- [x] P1: 完成 extractor 兼容入口，保持旧导入路径可用。
  - Owner: Codex
  - Definition of Done: `l2_decision.feature_store.extractors` 仍可导出关键入口与测试依赖私有类。
  - Blocking: 无。
- [ ] P1: 修复主机 `WinError 10106` 后补跑 feature_store/institutional_logic pytest。
  - Owner: Codex
  - Definition of Done: `scripts/test/run_pytest.ps1` 能执行目标用例。
  - Blocking: 主机 Python `asyncio` 初始化失败（环境问题，继承债务）。

## Parking Lot
- [ ] P2: 后续考虑将 registry lambda 提取为命名函数，进一步提升可读性。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] `extractors.py` 模块化拆分第三批次完成（2026-03-17 13:28 ET）

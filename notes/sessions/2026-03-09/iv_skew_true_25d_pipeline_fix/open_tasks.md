# Open Tasks

## Priority Queue
- [x] P0: 修复 L1->L2 skew 字段错读导致的 `IV SKEW=0` 常态化问题。
  - Owner: Codex
  - Definition of Done: L1 输出 `computed_delta`；L2 真25Δ提取正确读取 Arrow 字段并输出 `skew_25d_valid`。
  - Blocking: 无
- [x] P1: 修复 L3 阈值与无效值语义（`UNAVAILABLE` / `N/A`）并保持亚洲配色映射。
  - Owner: Codex
  - Definition of Done: `skew_25d_valid=0` 时输出 `UNAVAILABLE`；默认阈值为 `-0.10 / +0.15`。
  - Blocking: 无
- [x] P1: 补齐后端/前端定向回归与 SOP 同步。
  - Owner: Codex
  - Definition of Done: pytest 与 vitest 定向用例通过；SOP 更新说明真25Δ口径和 valid 标记。
  - Blocking: 无

## Parking Lot
- [ ] P2: 增加 skew 有效样本率运行时指标（用于盘中质量监控）。
- [ ] P2: 评估将 skew 计算下沉至更早层（L1 向量化路径）以减少 L2 特征重复开销。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] IV skew 真25Δ链路修复 + 阈值/展示语义修正 + 定向回归（2026-03-09 14:29 ET）

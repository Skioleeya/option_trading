# Open Tasks

## Priority Queue
- [x] P0: 修复 ActiveOptions “伪真实静态行”主因链（L0 flow 污染 + 合成行防伪 + 门禁升级）
  - Owner: Codex
  - Definition of Done: `chain_size>0` 时门禁要求 `row_quality=REAL`，合成 fallback 不再冒充真实可交易行；strict 通过
  - Blocking: 无
- [ ] P1: 用户终端在线验活留痕（网络栈健康场景）
  - Owner: User/Codex
  - Definition of Done: `verify_active_options_hotfix.ps1` 输出 `quality_real>=1` 且 PASS
  - Blocking: 当前 shell `WinError 10106`
- [ ] P2: 追加前端可观测（可选）展示 `row_quality/fallback_reason` 调试标签
  - Owner: Codex
  - Definition of Done: 仅 debug 视图可见，不影响主交易视图布局
  - Blocking: 需产品确认 UI 呈现方式

## Parking Lot
- [ ] 评估将 fallback 模式统计接入统一告警面板（Prometheus / log pipeline）。
- [ ] 评估将 `rows_real_non_synthetic` 作为会话健康 SLO 指标。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 完成 L0 `DEPTH` flow 字段隔离、ActiveOptions 行质量合同、diagnostics & gate 升级（2026-03-19 13:12 ET）

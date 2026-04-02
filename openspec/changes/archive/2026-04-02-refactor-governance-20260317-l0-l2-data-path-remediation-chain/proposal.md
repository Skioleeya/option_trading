## Why

静态审计已确认 L0->L2 数据通路存在 2 个 P1 连续性风险与 1 个 P2 性能风险：

1. L1 空快照路径丢失 `extra_metadata`，会中断 `rust_active/shm_stats/source_data_timestamp_utc` 连续性。
2. L0 未初始化/错误快照未稳定输出 `rust_active/shm_stats`，诊断链路在降级态弱化。
3. L0->L1 热路径仍以 `list[dict]` 每 tick 转 Arrow，未优先 zero-copy。

为避免修复过程引入边界漂移，采用父提案 + 子提案链路治理，分阶段执行并逐项验收。

## What Changes

1. 建立父提案治理框架，统一执行顺序、验收门槛与回滚准则。
2. 建立 3 个子提案：
   - `refactor-dependency-20260317-l1-empty-snapshot-metadata-continuity`（P1，优先执行）
   - `refactor-dependency-20260317-l0-fallback-snapshot-diagnostics-continuity`（P1，优先执行）
   - `refactor-bloat-20260317-l0-l1-arrow-zero-copy-path`（P2，随后执行）
3. 固化治理禁令并要求所有子提案严格遵守。

## Hard Governance Prohibitions

- 禁止使用复杂函数（单函数必须保持可审计、可拆分）。
- 禁止使用魔法数字（常量化并命名）。
- 禁止使用复杂嵌套（优先早返回与小函数）。
- 禁止模块耦合（保持层级方向与中立边界）。

## Scope

- 本父提案负责治理编排、顺序控制与证据收口。
- 本父提案不直接变更 runtime 行为。

## Child Proposals

- `refactor-dependency-20260317-l1-empty-snapshot-metadata-continuity` (order 1)
- `refactor-dependency-20260317-l0-fallback-snapshot-diagnostics-continuity` (order 2)
- `refactor-bloat-20260317-l0-l1-arrow-zero-copy-path` (order 3)

## Rollback

任一子提案出现以下任意情况，立即中止并回退到上一个已验证状态：

- 触发跨层违规 import 或反模式扫描命中。
- 合同字段语义发生未声明漂移。
- strict 门禁失败。
- 治理禁令（复杂函数/魔法数字/复杂嵌套/模块耦合）被破坏。


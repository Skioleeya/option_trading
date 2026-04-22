# Open Tasks

## Priority Queue
- [ ] P0: 完成受影响测试集回归（当前被环境阻断）。
  - Owner: Codex
  - Definition of Done: `scripts/test/run_pytest.ps1` 目标用例可完成采集与执行，并通过。
  - Blocking: WinError 10106 (`asyncio._overlapped` 无法加载)。
- [x] P1: 重新执行 strict validation（在 runtime 变更已纳入 session 元数据后）。
  - Owner: Codex
  - Definition of Done: `./scripts/validate_session.ps1 -Strict` 通过且包含 runtime 文件质量/链路门禁结果。
  - Blocking: 无。
- [x] P1: 完成 OpenSpec implementation 范围内代码落地（桥接 + 提取器 + 兜底）。
  - Owner: Codex
  - Definition of Done: Runtime 改动与对应单测更新均完成。
  - Blocking: 无。

## Parking Lot
- [ ] 观察 Rust depth 体积映射策略是否需要由 SHM schema 补充 bid/ask size 后再精化。
- [ ] 增加端到端审计样本，验证 `300/300=0` 退化模式消失。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Runtime implementation landed for L0/L1/L2 microstructure feature chain (2026-03-17 12:12 ET)
- [x] Strict validation passed for active session with quality + openspec gates (2026-03-17 12:17 ET)

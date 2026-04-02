# Tasks

## Scope
- [x] 锁定本提案目标范围：Rust SHM 微结构桥接 + L2 impact/turnover 特征链路修复
- [x] 明确非目标范围：不做 L4 UI 语义改造，不做广义重构拆分

## Implementation
- [x] 在 L0 Rust SHM 消费路径补齐 depth/trade -> L1 `on_depth/on_trade` 驱动链路
- [x] 修复 L2 `peak_impact/max_impact` 对 `RecordBatch` 与 `computed_gamma` 的兼容提取
- [x] 实现 `turnover_velocity` 的受控兜底策略（WS 优先，REST 仅兜底）
- [x] 增补结构化诊断日志，保证降级可观测、不可静默

## Verification
- [x] 运行相关 pytest（通过 `scripts/test/run_pytest.ps1`）
- [ ] 覆盖回归场景：
  - [ ] depth/trade 驱动后 `vpin_composite` 与 `bbo_imbalance_ewma` 非常零
  - [ ] `RecordBatch` 路径下 `peak_impact/max_impact` 非默认零
  - [ ] WS 缺失 turnover 时兜底生效，WS 恢复后回到 WS 优先
- [ ] 运行 `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`
- [x] 通过 OpenSpec 链路门禁（含 `check_openspec_chain.py`）

## DoD
- [ ] 目标字段不再在有效行情窗口出现长期全零退化模式
- [x] 无跨层违规 import 或架构边界退化
- [x] 变更可回滚、可审计，handoff 完整记录命令与结果

# Tasks

## Scope
- [x] 锁定目标文件清单（Top N）
- [x] 标记非目标范围（避免扩散）

## Implementation
- [x] 重构实现（仅本主题）
- [x] 边界扫描（无跨层违规 import）
- [x] 魔法数治理（若本主题涉及）

## Verification
- [x] 相关测试通过（scripts/test/run_pytest.ps1）
- [x] 指标达标（见量化门槛）
- [x] SOP 同步或写明 SOP-EXEMPT

## DoD
- [x] 复杂度/嵌套/长度/重复率达到阈值
- [x] 无行为回归
- [x] 变更可回滚、可审计

## Phase 1 - Baseline and Scope Freeze
- [x] 盘点 app 主路径与 L0 旧入口耦合点
- [x] 冻结 L0 新快照合同与非目标算法范围
- [x] 确定 `l0_ingest/v2` 单向目录布局

## Phase 2 - Neutral Contract Extraction
- [x] 提取 Arrow option-chain schema 到 shared 中立模块
- [x] 提取 Rust SHM bridge 到 shared 中立模块
- [x] 保持 L1 兼容 re-export

## Phase 3 - L0 V2 Worktree
- [x] 构建 `source/services/state/projection/facade` 工作树
- [x] 接入 runtime/subscription/iv_sync/orchestrator 旧基础件
- [x] 保证 L0 V2 主路径不 import `l1_compute`

## Phase 4 - App Hard Cut
- [x] `app/container.py` 切到 `l0_ingest.v2.OptionChainBuilder`
- [x] `lifespan` 切到 `fetch_snapshot()`
- [x] `compute_loop` 切到 `fetch_snapshot(include_chain_arrow=True)`

## Phase 5 - Contract Cleanup
- [x] 移除 ActiveOptions 输入适配对 L0 `aggregate_greeks` fallback
- [x] 移除 ActiveOptions 输入适配对 L0 `ttm_seconds` fallback
- [x] 让 L0 snapshot 投影不再暴露 legacy compute 字段

## Phase 6 - Rust Source Split
- [x] 将 `l0_rust/src/lib.rs` 拆分为 core/rest/helper/row 模块
- [x] 保持 `RustIngestGateway` Python 入口名称不变
- [x] 确保所有 Rust 源文件低于 400 行

## Phase 7 - Tests and Gate Prep
- [x] 执行 shared/app/L1 目标回归
- [x] 执行 L0 helper/bridge 目标回归
- [ ] 执行 `scripts/validate_session.ps1 -Strict`

## Phase 8 - Handoff and Closure
- [x] 同步 OpenSpec 记录
- [x] 同步 SOP 文档
- [ ] 回填 strict validation 结果到 session/context/handoff

PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 5
BLOCKED_BY: none

## Why

`l0_ingest/v2` 已成为 app 主路径，但 `l0_ingest` 包内仍残留旧 `feeds` 平铺结构、顶层业务模块和被跟踪的构建元数据，导致：

1. 目录边界与真实运行路径不一致，贡献者仍可能继续把业务逻辑写回旧平铺位置。
2. `v2` 内部依赖仍通过旧路径穿透，单向依赖树名义成立、实现上未完全收口。
3. `l0_ingest` 源码树混入 `dist-info` 等构建元数据，结构扫描与 handoff 审计噪声上升。

## What Changes

1. 将旧 `feeds/*` 与 `subscription_manager.py` 按职责并入 `l0_ingest/v2` 的分层子包。
2. 统一 `v2` 内部依赖与测试引用，移除仓内对 `l0_ingest.feeds.*` / `l0_ingest.subscription_manager` 的运行时依赖。
3. 重写 `l0_ingest/README.md` 与相关 SOP，声明 `v2` 为唯一正式工作树并禁止 L0 扁平化目录回潮。
4. 清退被跟踪的 `l0_ingest/l0_rust-0.1.0.dist-info/*`。

## Scope

- 目标：`l0_ingest/*`, `app/*`, `docs/SOP/*`, `openspec/changes/refactor-governance-20260324-l0-ingest-structure-governance/*`
- 同步：`notes/sessions/2026-03-24/l0-ingest-structure-governance/*`, `notes/context/*`
- 非目标：L1/L2/L3 算法语义变更

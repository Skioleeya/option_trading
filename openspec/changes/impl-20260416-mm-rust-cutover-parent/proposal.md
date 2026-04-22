PARENT_CHANGE_ID: none
DEPENDENCY_ORDER: 0
BLOCKED_BY: none

## Why

`v1.1.0-MM-Edition` 要求将期权流监控从权利金统计升级为机构化微观结构与 Greeks 敞口追踪，并以 Rust owner 为主落地到生产链路。当前仓库已具备 L0 Rust 主路径，但 trade condition 与 midpoint/tick-rule 链路仍缺失关键字段贯通，且 MM 功能未形成有序子提案执行链。

## What Changes

1. 建立 `MM Rust Cutover` 父提案，定义子提案执行顺序与关门标准。
2. 要求每个子提案在进入下一步前执行字段一致性检查：OpenSpec 字段定义 = runtime schema = payload/csv 输出。
3. 约束第一波（Wave1）先完成 L0 条件码贯通与 MVP Rust MM 核心落地。

## Child Order

1. `impl-20260416-mm-rust-cutover-wave1-l0-condition-and-mm-core`
2. `impl-20260416-mm-rust-cutover-wave2-l1-l2-rust-runtime`（已完成）
3. `impl-20260416-mm-rust-cutover-wave3-l3-assembly-rust-runtime`（已完成）
4. `impl-20260416-mm-rust-cutover-wave4-l4-ui-runtime`
5. `impl-20260416-mm-rust-cutover-wave5-l4-activeoptions-regression`

## Scope

In:
- OpenSpec 治理链
- L0 trade condition passthrough 合同
- Wave1 的 Rust MM 核心函数与 MVP 接入

Out:
- Wave2/Wave3 的完整运行时代码迁移（由后续子提案执行）

## Verification Gate

1. 子提案必须附带 strict validate 输出。
2. 子提案必须更新至少一个相关 SOP 文件或写明 `SOP-EXEMPT`。
3. 父提案关闭前必须有所有子提案证据链接与字段一致性核验记录。

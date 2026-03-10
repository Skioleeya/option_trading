# Project State

## Snapshot
- DateTime (ET): 2026-03-10 17:24:21 -04:00
- Branch: master
- Last Commit: 082c8e8
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 完成“耦合点专项审计与修复”，闭环 P0/P1 级耦合点并通过 strict gate。
- Scope In:
  - L4 store 跨日 sticky 与历史污染隔离（时间/会话耦合）。
  - L4 右栏模型本地主题映射（前后端样式语义耦合）。
  - L3 ActiveOptions 行协议转换单点收敛（协议键散落耦合）。
  - L2 Guard 阈值配置化（配置耦合）。
  - 右栏组件 selector 路径集中化（隐式协议路径耦合）。
- Scope Out:
  - 不改动 WebSocket 对外字段结构。
  - 不改动 L0/L1 运行时热路径算法。

## What Changed (Latest Session)
- Files:
  - l4_ui/src/store/dashboardStore.ts
  - l4_ui/src/store/__tests__/dashboardStore.test.ts
  - l4_ui/src/components/right/tacticalTriadModel.ts
  - l4_ui/src/components/right/skewDynamicsModel.ts
  - l4_ui/src/components/right/ActiveOptions.tsx
  - l4_ui/src/components/right/MtfFlow.tsx
  - l4_ui/src/components/right/SkewDynamics.tsx
  - l4_ui/src/components/right/TacticalTriad.tsx
  - l4_ui/src/components/right/DecisionEngine.tsx
  - l4_ui/src/components/left/DepthProfile.tsx
  - l4_ui/src/components/left/MicroStats.tsx
  - l4_ui/src/components/left/WallMigration.tsx
  - l4_ui/src/components/center/Header.tsx
  - l4_ui/src/components/__tests__/skewDynamics.model.test.ts
  - l3_assembly/events/active_options_contract.py
  - l3_assembly/presenters/active_options.py
  - l3_assembly/assembly/payload_assembler.py
  - l2_decision/guards/rail_engine.py
  - shared/config/agent_g.py
  - shared/config_cloud_ref/agent_g.py
  - docs/SOP/L2_DECISION_ANALYSIS.md
  - docs/SOP/L4_FRONTEND.md
- Behavior:
  - `dashboardStore` 新增 ET 交易日归一化，跨日禁止 sticky 保留旧 `ui_state`，并对 `atmHistory` 做交易日隔离。
  - `TacticalTriad` / `SkewDynamics` 前端 model 改为状态驱动本地主题映射，不再直接信任后端 class token。
  - `ui_state` 深层路径 selector 收敛到 store 导出函数，减少协议键散落。
  - ActiveOptions dict->typed row 转换收敛到单一契约函数，避免双实现漂移。
  - Guard 参数由 `settings.guard_*` 配置驱动，去除策略阈值硬编码耦合。
- Verification:
  - 前端 vitest（6 files / 39 tests）通过。
  - 后端 pytest 定向（l2 guards + l3 presenters/assembly，113 tests）通过。

## Risks / Constraints
- Risk 1: 仓库当前存在大量与本会话无关的脏文件，提交时需严格按会话改动范围筛选。
- Risk 2: 运行环境沙箱对临时目录写入有限制，部分 pytest 需提权运行才能反映真实结果。

## Next Action
- Immediate Next Step: 执行并通过 `scripts/validate_session.ps1 -Strict`，然后输出耦合清单与回归结论。
- Owner: Codex

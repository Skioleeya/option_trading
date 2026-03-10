# Open Tasks

## Priority Queue
- [x] P0: L1 MTF 几何状态机替换与多周期解耦
  - Owner: Codex
  - Definition of Done: `mtf_iv_engine` 与 `reactor` 不再使用同一瞬时快照驱动三周期，输出纯 `state+physical scalars`
  - Blocking: 无
- [x] P0: L3/L4 MTF 合同硬切与样式字段移除
  - Owner: Codex
  - Definition of Done: `MTFFlowState` 与前端类型不再含 `z/strength/align_color/dot_color...`
  - Blocking: 无
- [x] P0: 前端白名单防线落地
  - Owner: Codex
  - Definition of Done: `mtfFlowModel` 仅基于 `FlowState` 本地 `Record` 映射输出视觉 token，忽略后端样式输入
  - Blocking: 无
- [x] P1: 定向回归测试
  - Owner: Codex
  - Definition of Done: L1/L2/L3 pytest 与 L4 Vitest 目标集通过
  - Blocking: 无
- [x] P0: 零妥协 4 片段硬化
  - Owner: Codex
  - Definition of Done: 移除 L2/L3 旧语义回退、L3 ActiveOptions 可视字段不出 payload、L4 共识条本地映射、脏 state 强制归零
  - Blocking: 无
- [x] P0: Active Options 固定 5 行（后端强制补齐）
  - Owner: Codex
  - Definition of Done: 后端空盘/稀疏场景补齐到 5 行，L3 透传 `is_placeholder/slot_index`，L4 固定槽位渲染并本地兜底
  - Blocking: 无
- [x] P0: snapshot_version_iv_drift 探针去硬编码与降噪
  - Owner: Codex
  - Definition of Done: 漂移阈值全部来自配置，激活逻辑增加持续时长门限，避免 IV 平台期误报风暴
  - Blocking: 无
- [x] P1: Longbridge 历史K线时间戳 ET 归一化 MVP 校验脚本
  - Owner: Codex
  - Definition of Done: 可一键拉取 `SPY.US` 1m 历史K线并输出 raw/ET/UTC 对照，确认 naive 时间戳按 ET 解释
  - Blocking: 无
- [x] P1: MOMENTUM 阈值校准工具链（K线先行、Research接口预留）
  - Owner: Codex
  - Definition of Done: `tools/momentum_calibration` 模块化目录 + Stage1/2/3 CLI + 输出契约 + 单元测试通过
  - Blocking: 无

## Parking Lot
- [ ] P2: 处理仓内既有 `debugHotkey.integration.test.tsx` TypeScript 错误，恢复 `npm --prefix l4_ui run build` 全绿
- [ ] P2: 清理未使用的 `l3_assembly/presenters/ui/mtf_flow` 目录残留

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] MTF Flow 几何重构 + 前端白名单防线完成（2026-03-10 12:09 ET)
- [x] 4 片段零妥协加固完成并完成定向回归（2026-03-10 12:37 ET)
- [x] Active Options 固定 5 行重构完成并通过回归（2026-03-10 13:04 ET)
- [x] drift probe 配置化降噪完成并通过回归（2026-03-10 13:26 ET)
- [x] Longbridge 历史K线 ET 校验 MVP 脚本完成并实测（2026-03-10 14:10 ET)
- [x] MOMENTUM calibration 工具链完成并实跑 Stage1/2/3（2026-03-10 14:37 ET)

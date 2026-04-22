# Open Tasks

## Priority Queue
- [x] P0: 修复 WS 体积脏值污染 Active Options 排榜
  - Owner: Codex
  - Definition of Done: 脏值不再锁定 WS owner；REST fallback 可回填；新增回归测试通过
  - Blocking: 无
- [x] P1: Active Options 归一化层增加体积上限兜底
  - Owner: Codex
  - Definition of Done: 超大 `volume/current_volume` 在 normalize 阶段归零并通过测试覆盖
  - Blocking: 无
- [ ] P1: 在线验活（/health + /debug + /history）
  - Owner: User
  - Definition of Done: `verify_active_options_hotfix.ps1` PASS 且 `/history` 无异常超大 `volume`
  - Blocking: 当前环境无法启动 backend 子进程

## Parking Lot
- [ ] 继续追踪底层根因：WS 原始字段是否间歇携带字节错位值（需加 Rust/L0 原始采样日志）
- [ ] 评估 SHM join 场景下多实例并发写保护（必要时增加 producer 实例守卫）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 新增失败用例复现 `turnover>0 + volume 脏值 + current_volume=0` 污染路径（2026-03-19 16:46 ET）
- [x] `ChainStateStore` 增加 WS 体积可信上限过滤与 dropped 诊断计数（2026-03-19 16:47 ET）
- [x] Active Options normalize 增加第二层体积上限兜底（2026-03-19 16:48 ET）
- [x] `verify_active_options_hotfix.ps1` 判定口径调整为 `real_rows` + `missing_turnover`（2026-03-19 16:48 ET）
- [x] 定向 pytest 回归通过（35 + 10）(2026-03-19 16:49 ET)

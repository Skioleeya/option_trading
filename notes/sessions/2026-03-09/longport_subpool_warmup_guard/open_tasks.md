# Open Tasks

## Priority Queue
- [x] P0: 订阅池硬上限落地（<=500），refresh/manual 两路径统一裁剪策略。
  - Owner: Codex
  - Definition of Done: target_symbols 与 manual subscribe 都不会超过官方 500 上限，超限有日志。
  - Blocking: 无
- [x] P0: warm-up/REST 批次权重安全化，禁止 weight 超过 symbol_burst。
  - Owner: Codex
  - Definition of Done: warm-up/Tier2/Tier3/research 批次受 limiter.max_symbol_weight 约束，acquire 超限直接拒绝。
  - Blocking: 无
- [x] P1: RateLimiter 官方限制钳制（10/s, burst 10, concurrent 5）与守卫测试补齐。
  - Owner: Codex
  - Definition of Done: 配置误设为超限值时运行时自动钳制；新增单测通过。
  - Blocking: 无
- [ ] P1: 双栈长连接策略收敛（单账户单长连接约束）。
  - Owner: Codex
  - Definition of Done: 形成并实现单长连接方案（Rust-only 或 single shared quote path），并在 SOP 明确。
  - Blocking: 现有 Python REST + Rust WS 双栈拓扑耦合较高，需方案评审。

## Parking Lot
- [ ] P2: 为 FeedOrchestrator/IVSync 增加“超 500 候选池裁剪后 warm-up”集成回归。
- [ ] P2: 增加 runtime 指标：`subscription_pool_size`, `subscription_dropped_count`, `limiter_clamped`.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Quote API 订阅池与 warm-up 限制守卫落地（2026-03-09 10:44 ET）

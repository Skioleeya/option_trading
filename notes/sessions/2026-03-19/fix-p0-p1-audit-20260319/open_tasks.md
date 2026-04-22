# Open Tasks — Session: fix-p0-p1-audit-20260319

## Completed This Session
- [x] P0-1: chain_state_store — 移除 apply_event() OI 直写（BUG-8）
- [x] P1-5a: chain_state_store — 暴露 last_spot_update 公开属性
- [x] P1-5b: feed_orchestrator — 用公开属性替代私有访问
- [x] P1-6: iv_baseline_sync — _sort_by_proximity() 接受 symbol_to_strike dict
- [x] P1-1: l1_compute/reactor — wall_tracker 传入真实 Wall 成交量
- [x] P1-2: l1_compute/reactor — VIB engine 传入真实 OTM call/put volume
- [x] P1-3: l1_compute/reactor — VPIN 选最 ATM symbol
- [x] P0-2: vanna_flow_analyzer — 三处静默异常加日志
- [x] P2-6: vanna_flow_analyzer — _was_in_danger_zone 在 __init__ 和 reset() 声明
- [x] P0-3: l2_decision/reactor — decide_sync() 改用 asyncio.run()
- [x] P1-4: l2_decision/reactor — IV regime 映射加注释
- [x] P1-7: agent_g — vrp=None skip 加 debug 日志
- [x] P3-5: agent_g — vrp None f-string crash 防护

## Carried Forward (Next Session)
- [ ] P2: l2_decision 集成测试 — 验证 decide_sync asyncio.run 行为（DUE: 2026-03-21）
- [ ] P2: P1-6 完整接线 — OptionChainBuilder.initialize() 向 IVBaselineSync.start() 注入 get_strike_fn（DUE: 2026-03-21）
- [ ] P2-P3: 其余审计 P2/P3 项（MTF buffer、warning 滥用、dead comment、typing 混用）（DUE: 2026-03-24）

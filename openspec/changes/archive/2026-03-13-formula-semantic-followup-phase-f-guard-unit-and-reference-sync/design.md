## Context

`vol_risk_premium` 与 `VRPVetoGuard` 不能简单合并：

- 前者是 live feature proxy
- 后者是 guard 专用 heuristic

但它们都必须完成单位治理，否则 `% points` / decimal fraction 仍会混写。

## Decisions

1. 不把 guard 直接切到 `vol_risk_premium`
2. 新增/明确 `guard_vrp_proxy_pct = ATM_IV(%) - realized_vol_proxy(%)`
3. `realized_vol_proxy(%)` 继续由 `vol_accel_ratio` 代理推导，保持 guard 方向行为连续
4. `guard_vrp_entry_threshold` / `guard_vrp_exit_threshold` 文档化为 `% points`
5. 兼容窗口内旧 decimal 输入自动归一到 `% points`

## Test Plan

- guard tests 覆盖 `0.15/0.13` 与 `15.0/13.0` 等价性
- helper/unit tests 覆盖 `guard_vrp_proxy_pct`
- 文档/参考配置静态检查覆盖 live config 与 cloud ref 一致

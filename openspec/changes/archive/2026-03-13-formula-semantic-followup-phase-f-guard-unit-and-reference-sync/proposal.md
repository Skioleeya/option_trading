## Why

首轮整改后仍有两个 unit/reference residual：

1. `VRPVetoGuard` 仍沿用 guard 内部代理口径，未与 `% points` 单位治理闭合
2. `shared/config_cloud_ref/agent_g.py` 仍保留旧 `200M/1000M` 与旧 guard 阈值表述，和 live config 漂移

这会导致工程师在看 runtime guard、参考配置和文档时，继续读到两套不一致的单位语义。

## What Changes

1. 为 guard 明确单独合同：`guard_vrp_proxy_pct`
2. `VRPVetoGuard` 继续保留 “IV - realized-vol proxy” 思路，但统一按 `% points` 解释
3. 旧 `0.15/0.13` guard 配置继续兼容解释为 `15.0/13.0`
4. `shared/config_cloud_ref/agent_g.py` 与 live config 阈值、注释同步
5. `docs/IV_METRICS_MAP.md` 区分 `vol_risk_premium` 与 `guard_vrp_proxy_pct`

## Scope

- shared VRP guard helper / config normalization
- L2 `VRPVetoGuard`
- cloud reference config
- operator-facing formula/unit docs

## Parent

- `formula-semantic-followup-parent-governance`

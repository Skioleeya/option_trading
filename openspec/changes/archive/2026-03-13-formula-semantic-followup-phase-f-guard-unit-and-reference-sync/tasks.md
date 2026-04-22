## 1. Guard Contract

- [x] 1.1 在 shared 中立 helper 中定义 `guard_vrp_proxy_pct`
- [x] 1.2 将 `VRPVetoGuard` 统一到 `% points` 单位
- [x] 1.3 保留旧 `0.15/0.13` 输入兼容并归一为 `15.0/13.0`

## 2. Reference Sync

- [x] 2.1 同步 `shared/config_cloud_ref/agent_g.py` 到 live `20B/100B` 与 guard 阈值口径
- [x] 2.2 更新 `docs/IV_METRICS_MAP.md` 区分 `vol_risk_premium` 与 `guard_vrp_proxy_pct`
- [x] 2.3 更新至少一个 SOP / operator-facing 文档说明 guard 语义边界

## 3. Verification

- [x] 3.1 更新 guard 相关测试
- [x] 3.2 新增 helper/unit tests 覆盖阈值归一化
- [x] 3.3 通过 `scripts/test/run_pytest.ps1 l2_decision/tests/test_reactor_and_guards.py shared/tests/test_metric_semantics.py`

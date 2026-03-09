# Handoff

## Session Summary
- DateTime (ET): 2026-03-09 14:40:22 -04:00
- Goal: 修复右栏 IV SKEW 常态为 0 的 L0-L4 数据通路问题，并校准阈值与 UI 无效态语义。
- Outcome: 已完成真25Δ skew 口径落地、`skew_25d_valid` 契约新增、L3 `UNAVAILABLE/N/A` 展示路径、默认阈值修正与定向回归。

## What Changed
- Code / Docs Files:
  - l1_compute/reactor.py
  - l1_compute/tests/test_arrow.py
  - l2_decision/feature_store/extractors.py
  - l2_decision/tests/test_feature_store.py
  - l3_assembly/assembly/ui_state_tracker.py
  - l3_assembly/presenters/ui/skew_dynamics/mappings.py
  - l3_assembly/presenters/ui/skew_dynamics/presenter.py
  - l3_assembly/tests/test_ui_state_tracker.py
  - l3_assembly/tests/test_presenters.py
  - l3_assembly/tests/test_reactor.py
  - l4_ui/src/components/__tests__/skewDynamics.model.test.ts
  - l4_ui/src/components/__tests__/rightPanelContract.integration.test.tsx
  - shared/config/agent_b.py
  - shared/config_cloud_ref/market_structure.py
  - docs/SOP/L2_DECISION_ANALYSIS.md
- Runtime / Infra Changes:
  - L1 输出 `RecordBatch` 新增 `computed_delta`。
  - L2 skew 特征改为真25Δ（delta 最近邻）并新增 `skew_25d_valid`。
  - L3 当 `skew_25d_valid=0` 时输出 `UNAVAILABLE`，前端显示 `N/A` + `badge-neutral`。
  - skew 默认阈值统一为 `-0.10 / +0.15`。
- Commands Run:
  - powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId iv_skew_true_25d_pipeline_fix -Timezone "Eastern Standard Time" -ParentSession "2026-03-09/longport_startup_strict_connectivity"
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_arrow.py l2_decision/tests/test_feature_store.py l3_assembly/tests/test_ui_state_tracker.py l3_assembly/tests/test_presenters.py l3_assembly/tests/test_reactor.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_arrow.py l2_decision/tests/test_feature_store.py l3_assembly/tests/test_ui_state_tracker.py l3_assembly/tests/test_reactor.py l3_assembly/tests/test_presenters.py::TestSkewDynamicsPresenterV2
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l2_decision/tests/test_feature_store.py l3_assembly/tests/test_ui_state_tracker.py
  - npm --prefix l4_ui run test -- skewDynamics.model rightPanelContract.integration
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict

## Verification
- Passed:
  - scripts/test/run_pytest.ps1 l1_compute/tests/test_arrow.py l2_decision/tests/test_feature_store.py l3_assembly/tests/test_ui_state_tracker.py l3_assembly/tests/test_reactor.py l3_assembly/tests/test_presenters.py::TestSkewDynamicsPresenterV2 (72 passed)
  - scripts/test/run_pytest.ps1 l2_decision/tests/test_feature_store.py l3_assembly/tests/test_ui_state_tracker.py (51 passed)
  - npm --prefix l4_ui run test -- skewDynamics.model rightPanelContract.integration (2 files, 5 tests passed)
- Failed / Not Run:
  - scripts/test/run_pytest.ps1 ... l3_assembly/tests/test_presenters.py（全文件）首次运行出现 1 个历史失败：`TestDepthProfilePresenterV2::test_no_nan_inf_in_gex`（断言 `call_gex` 字段，与本次 skew 变更无关）。

## Pending
- Must Do Next:
  - 在目标运行环境观察 `ui_state.skew_dynamics.state_label=UNAVAILABLE` 的占比，确认真实数据覆盖率。
- Nice to Have:
  - 新增 skew 有效样本率监控指标（按分钟聚合）。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本次范围内无新增未解决交付项；历史无关测试失败未纳入本次修复范围
- DEBT-OWNER: Codex/User
- DEBT-DUE: 2026-03-12
- DEBT-RISK: 若忽略历史失败测试，可能掩盖 DepthProfile 契约老问题
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: DEBT-DELTA=0
- RUNTIME-ARTIFACT-EXEMPT: tmp/pytest_cache 由测试脚本管理，属允许的运行时产物

## How To Continue
- Start Command:
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict
- Key Logs:
  - 无新增专用日志；关注 pytest/vitest 输出
- First File To Read:
  - l2_decision/feature_store/extractors.py

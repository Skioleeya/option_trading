# Project State

## Snapshot
- DateTime (ET): 2026-03-13 16:20:00 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `1179556`
- Environment:
  - Market: `UNKNOWN` (offline fix + targeted regression)
  - Data Feed: `DEGRADED` (historical logs include Spot fallback failure)
  - L0-L4 Pipeline: `OK` (historical logs show connection open + recurring L0 fetch)

## Current Focus
- Primary Goal: 修复 ActiveOptions 数据卡死（空数据阶段仍保留旧榜单）并补齐可回归验证。
- Scope In:
  - `shared/services/active_options/runtime_service.py`
  - `shared/services/active_options/test_runtime_service.py`
  - `l4_ui/src/components/right/ActiveOptions.tsx`
  - `l4_ui/src/components/__tests__/activeOptions.render.test.tsx`
  - `docs/SOP/L4_FRONTEND.md`
  - `scripts/diag/check_active_options_freeze_rootcause.py`（复核运行）
- Scope Out:
  - 不改动 L0/L1/L2/L3 runtime 逻辑
  - 不变更 WS payload schema

## What Changed (Latest Session)
- Backend fix (`runtime_service`):
  - 空数据占位签名分支改为立即提交（绕过 3 tick 换榜门控），避免旧榜单粘滞。
  - 占位签名前缀常量化（`_PLACEHOLDER_SIGNATURE_PREFIX`）并统一用于签名构建与判定。
- Frontend fix (`ActiveOptions`):
  - 新增 `isDegraded`：当 5 行全为占位行时，右上角显示 `DEGRADED`，否则显示 `TOP BY VOL`。
- Regression tests:
  - 新增后端测试：真实签名 -> 占位签名应立即切换。
  - 新增前端测试：`DEGRADED/TOP BY VOL` 头部状态切换。
- SOP sync:
  - `docs/SOP/L4_FRONTEND.md` 增补 ActiveOptions 降级展示规则。

## Verification
- `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py -q` -> PASS (`11 passed`)
- `npm --prefix l4_ui run test -- src/components/__tests__/activeOptions.render.test.tsx` -> PASS (`6 passed`)
- `python scripts/diag/check_active_options_freeze_rootcause.py --json` -> historical logs still `YES/HIGH`, but source mode is now `emit_placeholders`.

## Risks / Constraints
- Risk 1: 诊断脚本读取历史日志，修复后短期仍可能显示 `retain_hits>0`（历史样本未滚动）。
- Risk 2: 需在新运行窗口复核日志，确认 `emit_placeholder_hits` 增长且不再出现 retain 文案。

## Next Action
- Immediate Next Step: 在新鲜运行日志上执行同一诊断脚本，确认 verdict 从历史 `YES` 过渡到当前行为 `NO/INCONCLUSIVE`。
- Owner: Codex

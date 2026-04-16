PARENT_CHANGE_ID: impl-20260416-mm-rust-cutover-parent
DEPENDENCY_ORDER: 5
BLOCKED_BY: impl-20260416-mm-rust-cutover-wave4-l4-ui-runtime

## Why

Wave4 后全量 `l4_ui` 回归仅剩 `activeOptions.render.test.tsx` 两处既有失败：一是 `slot_index` 异常场景触发重复 DOM key，二是测试语义仍假设前端按 VOL 本地排序，与当前“前端不做二次排序”的合同冲突。

## What Changes

1. `activeOptionsModel` 增加 `slot_index` 去重补位逻辑，确保 1..5 槽位唯一覆盖。
2. `activeOptions.render` 回归用例对齐现行合同：验证唯一槽位与“后端顺序优先”。
3. 执行 ActiveOptions 定向测试与 `l4_ui` 全量测试，恢复全绿。
4. 同步 L4 SOP 关于异常槽位输入的归一化规则。

## Scope

In:
- `l4_ui/src/components/right/activeOptionsModel.ts`
- `l4_ui/src/components/__tests__/activeOptions.render.test.tsx`
- `docs/SOP/L4_FRONTEND.md`

Out:
- L0-L3 排序策略修改
- ActiveOptions 视觉样式重构

## Verification Gate

1. `activeOptions.model` + `activeOptions.render` 测试通过。
2. `npm --prefix l4_ui run test` 全量通过。
3. strict validate 通过。

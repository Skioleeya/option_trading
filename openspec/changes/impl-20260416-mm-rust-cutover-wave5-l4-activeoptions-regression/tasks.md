## Scope

- [x] 锁定 Wave5 改动范围为 L4 ActiveOptions model/render tests + L4 SOP
- [x] 保持前端不引入跨层依赖与本地 VOL 二次排序

## Implementation

- [x] `activeOptionsModel` 增加 `slot_index` 去重补位
- [x] `activeOptions.render` 用例对齐最新合同语义
- [x] 同步 L4 SOP 槽位归一化规则

## Verification

- [x] 运行 `npm --prefix l4_ui run test -- src/components/__tests__/activeOptions.model.test.ts src/components/__tests__/activeOptions.render.test.tsx`
- [x] 运行 `npm --prefix l4_ui run test`
- [x] 运行 strict validate 并记录结果

## DoD

- [x] ActiveOptions 渲染不再出现重复 `slot-*` key
- [x] L4 全量测试恢复全绿
- [x] 无新增 >400 行 Python/Rust 文件

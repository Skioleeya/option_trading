## Scope

- [x] 锁定 Wave4 仅改动 L4 UI + L4 SOP
- [x] 保持 L4 不反向引入 L1/L2 计算依赖

## Implementation

- [x] 新增 `mmFlowModel` 合同归一化
- [x] 新增 `MmFlowCard` 渲染组件
- [x] 接入 `RightPanel` stable/default 双路径
- [x] 新增 model/render 单测

## Verification

- [x] 运行 `npm --prefix l4_ui run test -- src/components/__tests__/mmFlowModel.test.ts src/components/__tests__/mmFlowCard.render.test.tsx src/components/__tests__/rightPanelModel.test.ts src/components/__tests__/decisionEngine.render.test.tsx src/components/__tests__/rightPanelContract.integration.test.tsx`
- [x] 全量 L4 测试回归执行并记录失败归因（非本次改动）
- [x] 运行 strict validate 并记录结果

## DoD

- [x] L4 可观测到 `agent_g.data.mm_flow` 指标卡片
- [x] 无新增跨层违规 import
- [x] 无新增 >400 行文件

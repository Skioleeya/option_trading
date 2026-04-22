## Purpose

定义 Wave5 的 L4 ActiveOptions 回归修复合同：在不改变上游排序 owner 的前提下，修复槽位冲突导致的渲染不稳定。

## Requirements

### Requirement: ActiveOptions Slot Keys Must Stay Unique

#### Scenario: Duplicate Or Invalid Slot Index In Input Rows

WHEN L4 model 归一化 `active_options`
THEN 每行输出 `slot_index` 必须唯一且落在 `1..5`
AND 最终行集合必须覆盖完整槽位集合 `1..5`。

### Requirement: Frontend Must Not Locally Re-Sort By Volume

#### Scenario: Render Rows With Backend-Ordered Input

WHEN `ActiveOptions` 渲染列表
THEN 前端必须保持后端输入顺序
AND 不得按 `volume` 再次本地排序。

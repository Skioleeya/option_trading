## Purpose

建立 MM Rust Cutover 的父级治理合同，确保子提案按顺序执行并保持字段一致性。

## Requirements

### Requirement: Child Order Must Be Enforced

子提案必须按已声明顺序推进，禁止跳步。

#### Scenario: Next Child Starts Before Previous Child Completion

WHEN 前序子提案尚未完成验证证据
THEN 下一子提案不得进入实现阶段
AND 父提案不得推进关闭状态。

### Requirement: Field Consistency Check Is Mandatory

每个子提案必须在结束时执行字段一致性核验。

#### Scenario: Spec Field And Runtime Field Diverge

WHEN OpenSpec 字段定义与 runtime schema/payload 字段不一致
THEN 子提案必须保持打开状态
AND 不得进入下一子提案。

### Requirement: Parent Close Requires Child Evidence

父提案关闭必须包含全部子提案证据引用与 strict 验证结果。

#### Scenario: Parent Closure Missing Child Validation Evidence

WHEN 父提案缺少任一子提案 strict 验证证据
THEN 父提案关闭必须被拒绝。

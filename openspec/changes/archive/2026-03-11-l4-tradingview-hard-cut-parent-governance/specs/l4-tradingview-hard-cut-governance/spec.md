## ADDED Requirements

### Requirement: Parent-Child Dependency Order
硬切计划 SHALL 强制执行子提案顺序 `phase-a-foundation -> phase-b-center -> phase-c-right -> phase-d-left`。

#### Scenario: Out-of-Order Child Start
- **WHEN** 子提案 C 或 D 在其前置子提案未完成时启动
- **THEN** 父提案完成状态 MUST 被阻断。

### Requirement: Module Isolation Per Child
每个子提案 SHALL 仅实现一个主模块范围，禁止跨模块嵌套实现与交叉提交。

#### Scenario: Cross-Module Nested Change
- **WHEN** 子提案 B 同时引入 Right/Left 模块实现改动
- **THEN** 该子提案 MUST 视为边界违规并阻断完成。

### Requirement: Anti-Reverse-Dependency Gate
硬切执行过程中 SHALL 禁止反向依赖与跨层私有成员访问。

#### Scenario: Reverse Import Introduced
- **WHEN** 检测到 `l2 -> l3/l4` 或 `l3 -> l4` 反向导入
- **THEN** 当前子提案 MUST 回退并重新设计。

### Requirement: Parent Completion Gate
父提案 SHALL 仅在全部子提案完成且 strict 验证证据齐全时关闭。

#### Scenario: Missing Strict Evidence
- **WHEN** 任一子提案 handoff 缺少 `scripts/validate_session.ps1 -Strict` 通过证据
- **THEN** 父提案 MUST 保持打开状态。

## Purpose

定义 research persistence 的 canonical durable owner 合同，要求运行时只以单文件 canonical parquet 为 source of truth，并禁止静默降级写入。

## Requirements

### Requirement: Runtime Must Persist Through a Single Canonical Owner

#### Scenario: A Research Tick Is Appended

WHEN `ResearchFeatureStore.append_tick()` 成功提交一个 RTH 样本
THEN 运行时 MUST 只更新 `research/canonical/day_YYYYMMDD.parquet`
AND MUST NOT 写入 `research/raw`、`research/feature` 或 `research/label` 目录。

### Requirement: Invalid Persistence Inputs Must Fail Fast

#### Scenario: Source Timestamp Is Missing Or Invalid

WHEN `payload.data_timestamp` 缺失或不可解析
THEN `append_tick()` MUST 失败
AND MUST NOT 回退到进程当前时间。

#### Scenario: Spot Or MM Flow Payload Is Invalid

WHEN `snapshot.spot <= 0` 或 `payload.fused_signal.mm_flow` 缺失
THEN `append_tick()` MUST 失败
AND MUST NOT 静默跳过该样本。

### Requirement: Canonical Commit Must Be Atomic

#### Scenario: Canonical Rewrite Fails During Commit

WHEN 当日 canonical 新版本在提交阶段失败
THEN 旧 canonical 文件 MUST 继续保持可读
AND 新样本 MUST NOT 以部分状态暴露给查询或归档路径。

### Requirement: Label Recovery Must Rebuild From Canonical

#### Scenario: Backend Restarts During The Label Horizon

WHEN backend 在 60 分钟 label 窗口内重启
THEN `ResearchFeatureStore` MUST 仅基于最新 canonical 文件重建 pending label 队列
AND MUST 回填“已成熟但 label 为空”的历史行。

### Requirement: EOD Archive Must Project Frozen Research Outputs From Canonical

#### Scenario: End-Of-Day Archive Runs

WHEN EOD archive 处理某一交易日
THEN runtime research 输入 MUST 是该日 canonical parquet
AND staging 树 MUST 生成 `research_raw`、`research_feature`、`research_label` 冻结产物后再统一 publish。

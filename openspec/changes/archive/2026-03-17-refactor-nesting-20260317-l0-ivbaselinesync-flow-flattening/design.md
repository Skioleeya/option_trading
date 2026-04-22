## Design Summary

IVBaselineSync 重构为“流程编排 + 批次 helper”结构：

- `iv_baseline_sync.py` 保留生命周期与主循环编排。
- `iv_baseline_sync_support.py` 承担通用批处理工具：
  - 批次切片
  - IV/OI 字段解析
  - chunk 切分
  - symbol cap 计算

## Compatibility

- 对外接口不变：`warm_up`, `_staggered_sync`, `start/stop`。
- dedupe/cooldown/chunk 顺序保持一致。

## Quant Targets (Stage-1)

- warm_up 与 _staggered_sync 的嵌套层级显著下降。
- 关键路径重复解析逻辑收敛到单一 helper。

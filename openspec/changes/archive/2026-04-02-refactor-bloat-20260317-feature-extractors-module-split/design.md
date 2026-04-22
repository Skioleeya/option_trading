## Design Summary

采用“主题聚合 + 统一注册入口”拆分策略：

1. `extractors_flow.py`：spot roc / iv velocity / wall migration / turnover / max-impact / svol corr / mtf consensus
2. `extractors_skew.py`：skew/rr25/validity 与 25Δ 选腿逻辑
3. `extractors_volatility.py`：realized vol + realized VRP
4. `extractors_common.py`：共享 helper 与 `_safe` 安全封装
5. `extractors_registry.py`：`build_default_extractors` 与 reset 聚合入口
6. `extractors.py`：兼容层（对外入口与必要私有类 re-export）

## Constraints

- 对外接口与 feature name 不变
- 拆分后单文件 <= 450 行
- 禁止跨层导入污染

## Validation Plan

- feature store 单测回归
- recordbatch 路径回归
- strict + 质量门禁通过

## Bloat Metrics (Before/After)

- Before:
  - `l2_decision/feature_store/extractors.py`: 804 LOC
- After:
  - `l2_decision/feature_store/extractors.py`: 21 LOC
  - `l2_decision/feature_store/extractors_common.py`: 49 LOC
  - `l2_decision/feature_store/extractors_flow.py`: 271 LOC
  - `l2_decision/feature_store/extractors_skew.py`: 209 LOC
  - `l2_decision/feature_store/extractors_volatility.py`: 81 LOC
  - `l2_decision/feature_store/extractors_registry.py`: 229 LOC
- Result:
  - all split artifacts <= 450 LOC
  - `build_default_extractors` and `reset_all_default_extractors` contract retained

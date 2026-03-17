## Design Summary

采用“主题聚合 + 统一注册入口”拆分策略：

1. `extractors_flow.py`：turnover/max-impact/flow 相关
2. `extractors_skew.py`：skew/rr25/validity 相关
3. `extractors_volatility.py`：iv velocity/svol correlation/realized vol 相关
4. `extractors_common.py`：共享 helper 与安全封装
5. `extractors_registry.py`：`build_default_extractors` 聚合与注册

## Constraints

- 对外接口与 feature name 不变
- 拆分后单文件 <= 450 行
- 禁止跨层导入污染

## Validation Plan

- feature store 单测回归
- recordbatch 路径回归
- strict + 质量门禁通过

## Scope

- [x] 锁定 Wave1 文件范围与非范围
- [x] 定义 Wave1 字段合同

## Implementation

- [x] L0 schema/writer/gateway 增加 `trade_type/trade_session`
- [x] L0 trade payload 增加 midpoint tick-rule 方向判定
- [x] 新增 Rust MM core 函数并注册到 `shared_rust.services`
- [x] MVP 侧接入 Rust MM core 并升级 CSV 字段

## Verification

- [x] 运行 `scripts/test/run_pytest.ps1 scripts/test/test_longport_option_flow_mvp_live.py -k \"contract\"`
- [x] 运行 Rust 构建并更新 `shared_rust/services.pyd`
- [x] 运行 strict validate

## DoD

- [x] 字段一致性核验通过（spec = runtime = output）
- [x] 无跨层违规 import
- [x] 无新增 >400 行文件

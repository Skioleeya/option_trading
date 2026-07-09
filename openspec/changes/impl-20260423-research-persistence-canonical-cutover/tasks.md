## Scope

- [x] 锁定 research persistence runtime / archive / route / test / SOP 影响面
- [x] 明确旧三文件 owner 退出 runtime 合同

## Implementation

- [x] `ResearchFeatureStore` durable owner 切到 canonical 单文件模型
- [x] `append_tick()` 改为严格输入校验并删除静默降级
- [x] Rust 存储原语切到整日重写 + 原子替换
- [x] pending label 恢复与补齐改为基于 canonical
- [x] EOD archive / settle guard 切到 canonical 输入
- [x] SOP 同步 canonical owner 语义

## Verification

- [x] 相关测试通过（`python manage.py run-pytest` 定向 research/history/health/EOD 套件）
- [x] 行为回归覆盖 strict timestamp / spot / mm_flow / restart recovery / archive freeze
- [x] `python manage.py validate-session --strict`
- [x] `python manage.py start-all`

## DoD

- [x] runtime 不再写 `research/raw|feature|label`
- [x] canonical 提交失败时旧文件保持可读且不暴露半提交
- [x] `/api/research/features` 与 `/history?view=feature` 对外 shape 不变
- [x] handoff 记录验证命令输出与 SOP 更新

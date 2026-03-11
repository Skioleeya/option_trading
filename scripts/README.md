# Scripts — 运维与测试工具箱

该目录包含系统运维、性能监控、集成测试以及基础架构相关的辅助脚本。

## 目录结构

### 🛠️ [infra/](./infra/) — 基础设施与底层运维
- `redis-start.bat`: 一键启动 Redis 服务（端口 6380）。
- `audit_deg_flow.py`: 审计数据流一致性。

### 🔍 [diag/](./diag/) — 状态诊断与数据核查
- `check_gex_status.py`: 实时核查 GEX 暴露分布与中性点位置。
- `check_fused_signal.py`: 检测 L2 决策引擎信号状态。
- `check_atm_root.py`: 验证 ATM 合约根节点元数据。

### 🧾 [diagnostics/](./diagnostics/) — 在线对账与 EOD 归档
- `reconcile_net_gex_online.py`: WS 原始 `net_gex` 与前端展示逐 tick 对账证据导出。
- `reconcile_depth_profile_online.py`: Depth Profile 逐 tick 对账证据导出。
- `eod_bucket_archive.py`: 收盘后按规则阈值分桶（7 类，主标签唯一：`high_vol_open/gap_trend_day/vol_crush_day/pinning_day/whipsaw_day/trend_day/range_day`），输出 `daily/by_regime` manifest 与质量报告。

### ⏱️ [ops/](./ops/) — 运维调度脚本
- `register_eod_bucket_task.ps1`: 生成/注册 EOD 分桶计划任务（16:01 主任务 + 17:00 重试）。
- `run_eod_bucket.ps1`: 计划任务调用入口（按当天日期执行 EOD 分桶脚本）。

### ⚡ [perf/](./perf/) — 性能分析与资源监控
- `perf_monitor.py`: 监控后端计算循环延迟与 WebSocket 推送频率。
- `cpu_certify.py`: CPU 计算耗时基线验证。
- `check_resource_usage.py`: 显存/内存/句柄等系统资源占用统计。

### 🧪 [test/](./test/) — 开发验证与回归测试
- `test_depth_profile.py`: **推荐**。WebSocket 端到端 GEX 计算流 live 验证。
- `test_l0_l4_pipeline.py`: 全链路（从数据拉取到 L4 协议层）回归测试。
- `test_iv_oi_pipeline.py`: 专项测试：IV 同步与 OI 缓存逻辑。
- `test_zero_copy.py`: 验证 Python 与 Rust 间的 Arrow 零拷贝内存效率。
- `test_t2_t3_pollers.py`: Tier 2/3 轮询流测试。
- `test_assembler.py`: L3 消息组装器单元测试。
- `test_ui_tracker.py`: 前端状态追踪器逻辑验证。
- `test_presenter.py`: 简单 Presenter 数据转换测试。
- `run_pytest.ps1`: 统一 `pytest` 入口，强制使用独立缓存目录 `tmp/pytest_cache`，并拒绝管理员上下文执行（防权限混用残留临时目录）。

## 运行建议

所有 Python 脚本应在根目录下运行，确保 `PYTHONPATH` 正确：

```powershell
# Windows PowerShell 示例
$env:PYTHONPATH='.'
python scripts/test/test_depth_profile.py
```

> [!TIP]
> 每次执行重大重构（如 AppContainer 拆解）后，请至少运行一次 `scripts/test/test_depth_profile.py` 确保核心链路闭环。

推荐统一入口：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test\run_pytest.ps1 l1_compute/tests/test_reactor.py -q
```

## 会话上下文脚本（新增）

- `new_session.ps1`: 创建一次改动的独立会话目录，并自动更新 `notes/context` 三文件指针。
- `new_session.ps1 -NoPointerUpdate`: 创建会话目录但不改写 `notes/context` 指针（用于并行准备/预创建会话）。
- `new_session.ps1 -Timezone <IANA|Windows>`: 指定会话时间基准（影响 session 路径日期/HHMM 与 `meta.yaml` 时间字段）。
- `validate_session.ps1`: 校验会话四文件完整性（`project_state/open_tasks/handoff/meta`）以及 context 指针一致性。
- `validate_session.ps1 -Strict`: 启用硬门禁（`commands/files_changed/tests_passed` 非空、债务门禁不降级、运行产物策略校验）。
- `new_session.ps1 -UseTimeBucket`: 可选按分钟桶创建会话目录（`YYYY-MM-DD/HHMM/<task-id>`）。

严格模式下运行产物策略：
- 默认禁止在 `files_changed` 中包含 `logs/*` 与 `data/atm_decay/atm*.json`。
- 如确需提交，`handoff.md` 必须填写 `RUNTIME-ARTIFACT-EXEMPT: <reason>`。

示例：

```powershell
# 创建新会话
powershell -ExecutionPolicy Bypass -File .\scripts\new_session.ps1 `
  -TaskId "1118_backend_cutoff_hotfix" `
  -Title "backend atm cutoff parity" `
  -Scope "hotfix only" `
  -Owner "Quant Backend" `
  -ParentSession "2026-03-06/1106_atm_decay_hotfix_mod"

# 按时间桶创建（可选）
powershell -ExecutionPolicy Bypass -File .\scripts\new_session.ps1 `
  -TaskId "1125_anchor_guard_refine" `
  -UseTimeBucket `
  -Title "anchor guard refine"

# 指定时区创建（IANA/Windows 均可）
powershell -ExecutionPolicy Bypass -File .\scripts\new_session.ps1 `
  -TaskId "1133_p2_tooling_followup" `
  -Title "p2 tooling followup" `
  -Timezone "America/New_York"

# 创建会话但不更新 context 指针（可选）
powershell -ExecutionPolicy Bypass -File .\scripts\new_session.ps1 `
  -TaskId "1132_parallel_p1_prep" `
  -Title "parallel prep only" `
  -NoPointerUpdate

# 校验当前 active session（默认）
powershell -ExecutionPolicy Bypass -File .\scripts\validate_session.ps1

# 校验指定 session
powershell -ExecutionPolicy Bypass -File .\scripts\validate_session.ps1 `
  -SessionPath "notes/sessions/2026-03-06/1118_backend_cutoff_hotfix"

# 严格模式校验（CI/提交流程建议）
powershell -ExecutionPolicy Bypass -File .\scripts\validate_session.ps1 `
  -Strict
```

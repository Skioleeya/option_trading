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
- `validate_session.ps1`: 校验会话四文件完整性（`project_state/open_tasks/handoff/meta`）以及 context 指针一致性。
- `new_session.ps1 -UseTimeBucket`: 可选按分钟桶创建会话目录（`YYYY-MM-DD/HHMM/<task-id>`）。

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

# 校验当前 active session（默认）
powershell -ExecutionPolicy Bypass -File .\scripts\validate_session.ps1

# 校验指定 session
powershell -ExecutionPolicy Bypass -File .\scripts\validate_session.ps1 `
  -SessionPath "notes/sessions/2026-03-06/1118_backend_cutoff_hotfix"
```

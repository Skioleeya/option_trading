# Scripts — 运维与测试工具箱

该目录包含系统运维、性能监控、集成测试以及基础架构相关脚本。Windows 硬切后，统一通过仓库根目录 `manage.py` 执行运维入口。

## 目录结构

### 🛠️ [infra/](./infra/) — 基础设施与底层运维
- `audit_deg_flow.py`: 审计数据流一致性。
- `redis/redis.conf.local`: Redis 本地配置（由 `redis-server` 消费）。

### 🔍 [diag/](./diag/) — 状态诊断与数据核查
- `check_gex_status.py`: 实时核查 GEX 暴露分布与中性点位置。
- `check_fused_signal.py`: 检测 L2 决策引擎信号状态。
- `check_atm_root.py`: 验证 ATM 合约根节点元数据。

### 🧾 [diagnostics/](./diagnostics/) — 在线对账与 EOD 归档
- `reconcile_net_gex_online.py`: WS 原始 `net_gex` 与前端展示逐 tick 对账证据导出。
- `reconcile_depth_profile_online.py`: Depth Profile 逐 tick 对账证据导出。
- `eod_bucket_archive.py`: 收盘后 canonical taxonomy 分桶归档。
- `wait_for_eod_sources_settle.py`: 归档前 required 源稳定门控。
- `check_eod_manifest_sync.py`: 校验 manifest 与源文件 size/hash/rows 一致性。

### ⚡ [perf/](./perf/) — 性能分析与资源监控
- `perf_monitor.py`: 监控后端计算循环延迟与 WebSocket 推送频率。
- `cpu_certify.py`: CPU 计算耗时基线验证。
- `check_resource_usage.py`: 显存/内存/句柄等系统资源占用统计。

### 📏 [policy/](./policy/) — 架构边界规则
- `layer_boundary_rules.json`: L0-L4 与 app 跨层导入约束规则。

### 🧪 [test/](./test/) — 开发验证与回归测试
- `test_l0_l4_pipeline.py`: 全链路（数据拉取到 L4 协议层）回归测试。
- `test_iv_oi_pipeline.py`: IV 同步与 OI 缓存逻辑。
- `test_zero_copy.py`: Python 与 Rust 间 Arrow 零拷贝验证。
- `live_market_test.py`: Rust ingest gateway 实盘连通性验证。

## 统一 CLI 入口（Windows）

在仓库根目录运行：

```bash
.venv\Scripts\python.exe manage.py --help
```

常用命令：

```bash
# 统一 pytest 入口
.venv\Scripts\python.exe manage.py run-pytest l1_compute/tests/test_reactor.py -q

# 架构边界扫描
.venv\Scripts\python.exe manage.py check-layer-boundaries

# 会话严格校验
.venv\Scripts\python.exe manage.py validate-session --strict

# 创建新会话
.venv\Scripts\python.exe manage.py new-session --task-id "1118_backend_cutoff_hotfix" --title "backend atm cutoff parity" --scope "hotfix only"

# 统一 Rust .pyd 编译入口（工作区 Cargo 目录）
.venv\Scripts\python.exe manage.py build-pyd --check --all
```

## 会话上下文命令

- `.venv\Scripts\python.exe manage.py new-session ...`: 创建会话目录。
- `.venv\Scripts\python.exe manage.py new-session ... --use-time-bucket`: 按分钟桶创建会话目录。
- `.venv\Scripts\python.exe manage.py new-session ... --update-pointer`: 同步 `notes/context/*` 指针。
- `.venv\Scripts\python.exe manage.py validate-session`: 校验会话四文件和指针一致性。
- `.venv\Scripts\python.exe manage.py validate-session --strict`: 启用硬门禁（`commands/files_changed/tests_passed` 非空、债务门禁、运行产物策略、质量门禁、OpenSpec 链路）。
- `.venv\Scripts\python.exe manage.py build-pyd ...`: 统一 Rust `.pyd` owner 构建入口；强制 `CARGO_HOME=tmp/cargo_home`、`CARGO_TARGET_DIR=tmp/cargo_target`，并在 `build` 成功后把产物安装到运行时 owner 路径（`shared_rust/*.pyd`、`shared/services/l0_runtime/_native_generated/*.pyd`、`.venv\Lib\site-packages\{rust_kernel,l1_rust}`）。

Redis 标准入口补充：

- `start-all` 默认使用仓库固定路径 `infra/bin/redis-server.exe`。
- 若主机需要临时覆盖，可显式传 `--redis-exe <abs-path>`；最终交付仍以仓库固定路径为准。

严格模式下运行产物策略：
- 默认禁止在 `files_changed` 中包含 `logs/*` 与 `data/atm_decay/atm*.json`。
- 如确需提交，`handoff.md` 必须填写 `RUNTIME-ARTIFACT-EXEMPT: <reason>`。

## EOD 调度（Windows Task Scheduler）

```bash
# 先生成任务预览
python manage.py register-eod-bucket-task --output-dir tmp/schtasks

# 安装/更新计划任务
python manage.py register-eod-bucket-task --apply
```

## 盘前自动启动调度（Windows Task Scheduler）

```bash
# 先生成任务预览
.venv\Scripts\python.exe manage.py register-start-all-task --output-dir tmp/schtasks

# 安装/更新计划任务
.venv\Scripts\python.exe manage.py register-start-all-task --apply
```

说明：
- 计划任务固定在工作日 `09:25` 触发。
- 实际执行命令为 `run-scheduled-start-all`，它会先执行标准 `start-all`。
- `start-all` 完成后，命令会用 `XNYS` 日历判断当天是否为美股交易日。
- 若当天不是美股交易日（如周末或美股休市节假日），任务会显式关闭刚拉起的 Redis / backend / frontend 栈。

## 运行建议

所有 Python 脚本应在仓库根目录下运行，确保 `PYTHONPATH` 正确。

```bash
$env:PYTHONPATH='.'
python scripts/test/test_depth_profile.py
```

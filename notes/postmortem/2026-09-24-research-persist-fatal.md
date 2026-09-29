# 2026-09-24 — 前端 "RDS STALLED"：研究数据落盘失败导致 L3 停机

## 症状

前端页面顶部连接标签显示 **RDS STALLED**（橙色），被理解为"Redis 失败"。
实际 Redis 全程健康 —— 故障在文件落盘。

## 时间线（美国东部时间 EDT）

| 时刻 | 事件 |
|---|---|
| 09:30:12 | backend (uvicorn :8001) 启动，pid 20560 / 20580 |
| 09:30:20 | 后端日志 `Connected to Redis at 127.0.0.1:6380` |
| 09:30:37 | frontend (:5173) 启动，pid 21012 |
| **09:32:31** | `[CRITICAL] [L3 Reactor] research_store append failed (fatal): OSError: Unable to remove the file to be replaced. (os error 1175)` |
| **09:32:31** | `[CRITICAL] [L3 Broadcast Loop] Fatal runtime stop: research_persistence` |
| 09:32:31 之后 | Redis warm tier 停在 `13:32:31Z`，2 小时无新快照；前端持续 `RDS STALLED` |

## 关键证据

| 检查项 | 命令 / 位置 | 结果 |
|---|---|---|
| Redis 进程 | `netstat -ano` | `memurai.exe` pid 6464 LISTENING :6380 |
| Redis 可用 | Redis `PING` | `+PONG` |
| Redis 写入 | `GET /debug/persistence_status` | `redis.connected=true`，`l3_store.warm_writes=118, warm_failures=0` |
| 后端健康 | `GET /health` | **503**，`fatal_runtime_error.source=research_persistence` |
| Redis 数据新鲜度 | `LRANGE spy:snapshots:latest 0 0` | 最新 `stored_at=2026-09-24T13:32:31.457437+00:00` |
| 前端文案来源 | `l4_ui/src/components/center/headerState.ts:40` | `'RDS STALLED'`（RDS = 前端实时数据流代号，非 Redis） |

## 根因

`l0_ingest/l0_rust/src/research_store_storage.rs` 的 Windows 分支用 `ReplaceFileW`
做原子替换（`replace_existing_file`，57–102 行）。该 API 在本机**系统性不可靠**。

探针实测（`tmp/wb_probe_replace_primitive.py`，各 60 轮）：

| 原语 | 失败次数 |
|---|---|
| `ReplaceFileW` | **13/60（21.7%）**，`GetLastError()` 恒为 0 |
| `os.replace` | **0/60** |

失败被设计为致命（`ResearchPersistenceFatalError`，`l3_assembly/reactor.py`）
→ compute loop 抛出 → L3 广播循环停止 → WebSocket 不再推送
→ 前端心跳 3 秒超时（`connectionMonitor.ts`）→ `RDS STALLED`。

`append_tick` 每秒执行"读整个 parquet → 追加一行 → 重写整个 parquet"，
21.7% 的单次失败率意味着几乎必然在数分钟内触发致命停机。

## 修复

### 1. 核心：绕开不可靠的 ReplaceFileW

新增 `shared/services/l0_runtime/durable_parquet_write.py`，由
`native_loader.py` 加载后包装 `service_research_write_parquet_rows`：

- 让 native 写到**不存在的 staging 路径** → 走 `atomic_write_bytes` 的
  `fs::rename` 分支（实测 0/40 失败）
- 再用 `os.replace` 做最终原子交换（实测 0/60 失败），带重试
- parquet 字节仍由 native 生成 → 落盘内容不变

### 2. 兜底：reactor 层重试

`l3_assembly/reactor.py` 的 `_append_research_tick` 增加有限次重试
（默认 3 次 × 150ms），重试耗尽仍 fatal —— 不静默降级。

### 3. 消除假绿

`infra/ops_cli/start_all.py` 的 `_verify_stack` 原先只检查端口 LISTENING，
后端已 fatal 仍打印 "All services are up"。现在 Backend 行额外要求
`GET /health == 200`。

## 新增配置

`shared/config/persistence.py`：

| 键 | 默认 | 用途 |
|---|---|---|
| `research_persist_max_attempts` | 3 | reactor 层 append 重试次数 |
| `research_persist_retry_delay_ms` | 150 | reactor 层重试间隔 |
| `parquet_swap_max_attempts` | 5 | `os.replace` 交换重试次数 |
| `parquet_swap_retry_delay_ms` | 50 | `os.replace` 交换重试间隔 |

## 验证

| 验证 | 方法 | 结果 |
|---|---|---|
| 修复有效 | 包装后重复写（目标已存在）60 轮 | **0/60 失败**（对照 13/60） |
| 数据保真 | 读回 60 行与写入比对 | 完全一致 |
| 回归 | `pytest`（4 个相关文件） | 22 passed |
| 非空转（摘掉修复） | 连跑 4 次 | 3 次报红（1–2 failed） |
| 非空转（装上修复） | 连跑 3 次 | 3/3 全绿 |
| 服务恢复 | 重启后端后观察 | backend 起至 `12:34:06` 的 `L3-PAYLOAD tick_id=23`；Redis 最新 `stored_at=2026-09-24T16:34:06Z`（此前停在 `13:32:31Z`）；`day_20260924.parquet` 24165 → 31637 字节；重启后 `research_store append failed` 无新增 |

## 运维注意

从自动化会话的后台任务里启动 `manage.py start-all`，**服务会随该会话进程一起被回收**
（Windows Job Object 行为，`start_new_session=True` 也挡不住）。日志能证明服务启动正常，
但会话一结束端口就没了。**长驻服务请在交互式终端里启动。**

## 遗留

- **Rust 工具链缺失**：`rustup toolchain list` → `no installed toolchains`，
  无法重编译 `.pyd`。根治应在 Rust 侧改用 `MoveFileExW` 或带重试的替换；
  当前以 Python 侧包装绕过。
- 残留文件 `data/research/canonical/.day_20260902.parquet.tmp-3236-1788356321434345000`
  （9 月 2 日同类失败的临时文件残留），未清理。
- `infra/ops_cli/test_start_all.py` 有 2 个测试因沙箱 `tmp_path` fixture 不可用而
  ERROR（既有问题，与本次改动无关）。
- `_verify_stack` 只在启动时刻校验 `/health`；**运行中失效**仍需外部监控。

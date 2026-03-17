## Phase 2-8 Execution Evidence

Updated at: `2026-03-17 18:01` (US/Eastern)

## Phase 2 - Split Plan

### Split module graph

- `runtime_service.py`: orchestration entry + pipeline orchestration + state commit policy
- `runtime_service_support.py`: pure helpers (normalize/filter, ranking, row formatting, placeholder/signature helpers)

### Migration sequence

1. 先抽离纯函数到 support 模块（无状态依赖）。
2. `runtime_service` 改为调用 support，保留兼容包装方法。
3. 回归测试确认行为不漂移，再执行门禁。

### Compatibility export strategy

- 对外公共 API 保持不变：
  - `ActiveOptionsRuntimeService.get_latest()`
  - `ActiveOptionsRuntimeService.update_background(...)`
- 保留类内 `_format_row/_rank_outputs/_build_ranked_candidate/...` 兼容包装，避免测试和潜在内部调用一次性断裂。

## Phase 3 - Extract Helpers

Added:

- `shared/services/active_options/runtime_service_support.py`
  - `normalize_chain_volume_fields`
  - `normalize_and_filter_chain`
  - `rank_outputs`
  - `format_row` / `placeholder_row` / `pad_rows`
  - `build_ranked_candidate`
  - `is_placeholder_signature`

Moved from runtime service:

- 方向/格式化/占位签名/排序/padding 等纯逻辑已迁移。

## Phase 4 - Orchestration Shrink

Changed:

- `shared/services/active_options/runtime_service.py`
  - 聚焦 orchestration:
    - `update_background`
    - `_run_flow_pipeline`
    - `_commit_or_hold_candidate`
  - 保留轻量 state guards 与兼容包装方法。

Before/After (runtime_service):

- line count: `384 -> 246`
- class method count: `21 -> 17`
- `update_background` line count: `34`（维持 guard-first）

## Phase 5 - Verification Prep

### Import relation and cycle check

Command:

```powershell
python - <<'PY'
# local module dependency graph + cycle check
PY
```

Observed:

- `runtime_service -> {deg_composer, flow_engine_d, flow_engine_e, flow_engine_g}`
- `runtime_service_support -> {}`
- `has_cycle: false`

## Phase 6 - Regression and Quality

### Targeted pytest

Command:

```powershell
./scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py app/loops/tests/test_housekeeping_gpu_dedup.py app/loops/tests/test_compute_loop_gpu_dedup.py
```

Observed:

- `19 passed`

### Quality gate

Command:

```powershell
python ./scripts/policy/check_quality_gates.py --repo-root . --config scripts/policy/quality_thresholds.json --meta-file tmp/session_validation_diag/bloat_quality_meta.yaml --output tmp/session_validation_diag/bloat_quality_gate.json
```

Observed:

- `status: PASS`
- `targets: runtime_service.py, runtime_service_support.py`
- `duplicate_windows: 0`

### Boundary scan

Command:

```powershell
./scripts/policy/check_layer_boundaries.ps1
```

Observed:

- pass

## Phase 7 - Strict Gate

Command:

```powershell
./scripts/validate_session.ps1 -Strict
```

Observed:

- pass (final session sync after evidence write)

## Phase 8 - Closure

### Quantified before/after

1. Runtime orchestration file size: `384 -> 246` lines (`-138`, about `-35.9%`).
2. Helper logic split-out: new support module `182` lines / `11` functions。
3. 回归稳定性：ActiveOptions + loop 相关目标集 `19/19` 通过。

### Risks and rollback

Residual risk:

- 兼容包装方法仍存在于 `runtime_service.py`，后续可在稳定窗口再逐步下沉或去除。

Rollback:

1. Revert `runtime_service.py` and `runtime_service_support.py`.
2. Re-run targeted pytest + strict.

### Parent backfill

Parent child execution status updated:

- `dependency`: done
- `nesting`: done
- `bloat`: done
- `magic-number`: pending

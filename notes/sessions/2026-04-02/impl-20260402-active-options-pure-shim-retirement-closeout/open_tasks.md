# Open Tasks

## Priority Queue
- [x] P0: 完成 `impl-20260402-active-options-pure-shim-retirement` 收口验证（Step 8/9）
  - Owner: Codex
  - Definition of Done: 残留模块路径扫描 0 命中 + 联合 consumer smoke `all-ok`
  - Blocking: 无
- [x] P0: 补齐目标验证证据
  - Owner: Codex
  - Definition of Done: 5 个分步 smoke 全绿；定向 pytest 全绿（`test_compute_loop_gpu_dedup.py`、`test_housekeeping_gpu_dedup.py`）
  - Blocking: `l2_decision/tests/` 目录不存在（提案命令路径过时，改为等价定向回归）
- [x] P0: 会话文档回填并通过 strict
  - Owner: Codex
  - Definition of Done: `meta/project_state/open_tasks/handoff` 回填完整且 strict 门禁通过
  - Blocking: 无

## Parking Lot
- [x] 无

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Step 8 精确残留扫描完成：`rg -n "shared\.services\.active_options_(engines|input)" ... -g "*.py"` 返回 0 命中（2026-04-02 18:45 ET）
- [x] Step 9 联合 consumer smoke 通过：`all-ok`（2026-04-02 18:45 ET）
- [x] 定向回归通过：`app/loops/tests/test_compute_loop_gpu_dedup.py`（2 passed）+ `app/loops/tests/test_housekeeping_gpu_dedup.py`（4 passed）（2026-04-02 18:47 ET）

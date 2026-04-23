## Context

研究持久化是 L3 runtime 的 durable owner，不允许出现半提交、静默降级或重启后 label continuity 断裂。旧实现把一个逻辑样本拆成 `raw/feature/label` 三类文件提交，天然无法提供跨文件原子性。

## Design

1. Durable owner
   - 运行时只保留 `research/canonical/day_YYYYMMDD.parquet`。
   - canonical schema 包含 feature 字段与 label 字段；未成熟 label 先写 `null`。

2. Write path
   - `append_tick()` 先严格校验输入，再加载当日 canonical 全量行。
   - 内存中更新已成熟 pending label，然后追加新样本。
   - 以整日 canonical 行集重写临时 parquet。
   - 提交阶段使用单文件原子替换，避免 `raw-only` / `feature-only` 半提交。

3. Recovery path
   - 启动时只读取当前交易日 canonical。
   - 恢复未成熟 pending label 队列。
   - 若发现“已成熟但 label 仍为空”的历史行，启动期直接回填并重写 canonical。

4. Read and archive path
   - `/api/research/features` 与 `/history?view=feature` 从 canonical 投影 feature 视图。
   - EOD archive 把 canonical 作为 runtime 输入，并在 staging 树内生成 `research_raw` / `research_feature` / `research_label` 冻结快照。

## Risk Controls

1. 不保留旧三文件 runtime 写路径，避免 owner 双轨漂移。
2. 不允许 `data_timestamp` 回退到 `Utc::now()`，保证 L0 源时间绑定不被破坏。
3. 研究持久化异常继续沿 fatal 链路上报，禁止 neutral payload 掩盖损坏。

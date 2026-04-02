## Design

### 1. ATM Live Continuity

- 保持现有 compute dedup 语义：重复 `snapshot_version` 不重跑 L1/L2。
- 但 dedup tick 仍执行 `AtmDecayTracker.update(chain, spot)`，因为 tracker 本身在数值不变时也会产出新的 live item timestamp。
- 若 tracker 产出新 ATM item，则在 `app/loops` 内基于上一份 `FrozenPayload` 生成一个仅替换 `atm` 与 `broadcast_timestamp` 的新 payload，继续沿现有 L3 governor / WS 路径广播。
- 不新增新协议字段；前端继续消费既有 `atm` 合同。

### 2. ATM History Sanitizer

- 在 `l1_compute.analysis.atm_decay` 内新增纯 helper，对 series points 做：
  - timestamp 解析
  - trade date 过滤
  - active trade date 的 future timestamp 过滤
  - normalized timestamp 去重
  - 升序排序
- storage 的 `append/get/recover/get_latest` 统一复用该 sanitizer。
- cold restore 若发现污染样本，恢复到 Redis 前只注入净化后的序列，并重写 cold JSONL 镜像以清除同日污染。

### 3. Contract and Risk Notes

- `timestamp` 继续表示 ATM sample event time，不改为 heartbeat/broadcast time。
- L3 不新增字段、不变更 delta 协议；只让 dedup tick 也能产出新的 `atm` 变化。
- sanitizer 只作用于 ATM history 存储层，不触碰其他 history 视图。

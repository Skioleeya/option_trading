# Tasks

## Scope
- [x] 锁定目标文件清单（Top N）
- [x] 标记非目标范围（避免扩散）

## Implementation
- [x] 重构实现（仅本主题）
- [x] 边界扫描（无跨层违规 import）
- [x] 魔法数治理（若本主题涉及）
- [x] startup bootstrap 接管 pending restore 后的 strict restore/discard
- [x] pending restore discard 后继续 fresh same-day capture

## Verification
- [x] 相关测试通过（scripts/test/run_pytest.ps1）
- [x] 指标达标（见量化门槛）
- [x] 在线验证 backend 重启后不再停留在 stale `662`，已 fresh-capture 新 `661` anchor
- [x] SOP 同步或写明 SOP-EXEMPT

## DoD
- [x] 执行 `scripts/validate_session.ps1 -Strict`
- [x] 核验 quality gate 与 openspec chain gate
- [x] 回填 session/context/handoff 证据
- [x] 复杂度/嵌套/长度/重复率达到阈值
- [x] 无行为回归
- [x] 变更可回滚、可审计

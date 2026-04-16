## Context

L4 `ActiveOptions` 当前契约要求：前端消费后端排序结果，不执行本地 VOL 重排；同时 UI 必须稳定渲染 5 个槽位并保证行 key 唯一。

## Design

1. 对每条真实行优先使用合法且未占用的 `slot_index`（范围 1..limit）。
2. 若 `slot_index` 重复/越界/缺失，则分配首个可用槽位。
3. 真实行处理完成后，对剩余槽位补齐 placeholder，保持 5 行显示与唯一 key。
4. render 测试不再假设本地 VOL 排序，改为验证“后端顺序保持 + 槽位唯一完整”。

## Consistency Rule

`slot_index` 仅作为槽位定位契约，不是本地排序触发器；排序 owner 仍在上游 runtime service。

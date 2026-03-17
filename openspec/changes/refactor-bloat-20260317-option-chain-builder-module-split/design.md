## Design Summary

在 dependency 子提案定义的接口边界上做最小侵入拆分：

1. `builder_orchestration`：生命周期与主循环编排。
2. `builder_rust_bridge`：Rust 事件消费与桥接逻辑。
3. `builder_payload_mapper`：事件字段转换与标准化。
4. `builder_callbacks`：depth/trade callback 分发与错误处理。

## Constraints

- 保持现有外部调用入口不变
- 不改变 payload 字段语义
- 拆分后任一文件不得超过 450 行

## Validation Plan

- 目标路径单测回归
- 关键桥接路径 smoke
- strict gate + 质量门禁通过

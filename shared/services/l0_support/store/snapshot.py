"""
快照类型定义

FrozenSnapshot  — 不可变的链状态快照
SnapshotVersion — 版本元数据
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional


@dataclass(frozen=True)
class SnapshotVersion:
    """快照版本元数据（不可变）"""
    version: int                    # 单调递增版本号
    created_at: float               # time.monotonic()
    seq_no: int = 0                 # 最后写入的 seq_no
    source: str = "unknown"         # 触发写入的来源


@dataclass(frozen=True)
class FrozenSnapshot:
    """
    不可变的链状态快照。

    所有字段必须是可哈希或可序列化类型，
    dict 字段需在存入前转为 frozenset / tuple。

    设计原则：
    - 读取端持有引用时，写入端创建新快照，互不影响
    - version_meta 提供完整审计信息
    """
    version_meta: SnapshotVersion

    # 核心链状态（对应 ChainStateStore 的字段）
    spot_price: float = 0.0
    spot_timestamp: float = 0.0
    atm_strike: Optional[float] = None

    # 序列化的期权链数据（key = 合约代码）
    # 使用 tuple of (symbol, bid, ask, oi, delta) 保持不可变
    chain_snapshot: tuple = field(default_factory=tuple)

    # 质量摘要
    last_nan_count: int = 0
    last_breaker_trips: int = 0

    @property
    def version(self) -> int:
        return self.version_meta.version

    @property
    def age_ms(self) -> float:
        return (time.monotonic() - self.version_meta.created_at) * 1000

    def is_fresh(self, max_age_ms: float = 2000.0) -> bool:
        """快照是否在有效期内"""
        return self.age_ms <= max_age_ms

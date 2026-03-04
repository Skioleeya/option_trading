"""
质量告警事件定义

DataQualityAlert — 单次 tick 质量告警
CircuitBreakerEvent — 断路器触发事件
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

from .base import BaseEvent, EventType, EventPriority


class AlertSeverity(Enum):
    INFO    = "info"
    WARNING = "warning"
    ERROR   = "error"
    CRITICAL = "critical"


class BreakerReason(Enum):
    TICK_JUMP        = "tick_jump"       # 价格跳变 > 5σ
    GAP_TIMEOUT      = "gap_timeout"     # gap > 3s
    OI_SURGE         = "oi_surge"        # OI 突变
    BID_GT_ASK       = "bid_gt_ask"      # 倒挂
    HTTP_429         = "http_429"        # API 速率限制
    CONSECUTIVE_FAIL = "consecutive_fail" # 连续失败


@dataclass
class DataQualityAlert(BaseEvent):
    """单次 tick 质量告警事件"""
    severity: AlertSeverity = AlertSeverity.INFO
    reason: str = ""
    field_name: Optional[str] = None     # 问题字段名
    raw_value: Optional[Any] = None      # 原始值
    corrected_value: Optional[Any] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.event_type = EventType.SYSTEM
        if self.severity in (AlertSeverity.ERROR, AlertSeverity.CRITICAL):
            self.priority = EventPriority.HIGH


@dataclass
class CircuitBreakerEvent(BaseEvent):
    """
    断路器触发事件

    触发后消费方应暂停对该 symbol 的处理，
    等待 reset_after_seconds 秒后自动恢复。
    """
    reason: BreakerReason = BreakerReason.TICK_JUMP
    z_score: Optional[float] = None      # Tick Jump 时的 Z-score
    gap_seconds: Optional[float] = None  # Gap Timeout 时的 gap 长度
    reset_after_seconds: float = 5.0     # 自动恢复时间
    is_open: bool = True                 # True=熔断中, False=已恢复

    def __post_init__(self) -> None:
        self.event_type = EventType.SYSTEM
        self.priority = EventPriority.CRITICAL

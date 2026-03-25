"""
数据质量报告系统

DataQualityReport : 单次 tick 的质量报告
QualityMetrics    : 聚合质量指标
QualityCollector  : 滚动窗口收集器
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Deque


@dataclass
class DataQualityReport:
    """
    单次 tick 的质量评估结果。

    由 SanitizePipelineV2.parse_with_quality() 产生。
    """
    symbol: str
    passed: bool = False
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    nan_fields: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.monotonic)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.passed = False

    @property
    def has_issues(self) -> bool:
        return bool(self.warnings or self.errors)

    @property
    def is_clean(self) -> bool:
        return self.passed and not self.errors

    def summary(self) -> str:
        parts = []
        if self.errors:
            parts.append(f"ERR:{len(self.errors)}")
        if self.warnings:
            parts.append(f"WARN:{len(self.warnings)}")
        return f"[{self.symbol}] {'PASS' if self.passed else 'FAIL'} {' '.join(parts)}"


@dataclass
class QualityMetrics:
    """
    聚合质量指标（通常以 1 分钟为滚动窗口）。

    字段：
        total_ticks  : 总 tick 数
        passed_ticks : 通过数
        nan_count    : NaN/Inf 被替换的字段次数
        gap_events   : gap 触发次数
        breaker_trips: 断路器触发次数
        oi_surges    : OI 突变次数
    """
    total_ticks: int = 0
    passed_ticks: int = 0
    nan_count: int = 0
    gap_events: int = 0
    breaker_trips: int = 0
    oi_surges: int = 0

    @property
    def pass_rate(self) -> float:
        return self.passed_ticks / max(1, self.total_ticks)

    @property
    def nan_rate(self) -> float:
        return self.nan_count / max(1, self.total_ticks)

    def to_dict(self) -> Dict[str, float]:
        return {
            "total_ticks": self.total_ticks,
            "pass_rate": self.pass_rate,
            "nan_rate": self.nan_rate,
            "gap_events": self.gap_events,
            "breaker_trips": self.breaker_trips,
            "oi_surges": self.oi_surges,
        }


class QualityCollector:
    """
    滚动窗口质量收集器。

    调用 record(report) 追踪每次 tick 的质量报告，
    调用 snapshot() 获取当前窗口的聚合指标。

    参数:
        window_size: 滚动窗口 tick 数（默认 1000）
    """

    def __init__(self, window_size: int = 1000) -> None:
        self._reports: Deque[DataQualityReport] = deque(maxlen=window_size)

    def record(self, report: DataQualityReport) -> None:
        self._reports.append(report)

    def snapshot(self, symbol: Optional[str] = None) -> QualityMetrics:
        """
        生成聚合指标快照。

        参数:
            symbol: 若指定，只统计该 symbol 的报告
        """
        reports = self._reports
        if symbol:
            reports = [r for r in reports if r.symbol == symbol]  # type: ignore[assignment]

        m = QualityMetrics()
        for r in reports:
            m.total_ticks += 1
            if r.passed:
                m.passed_ticks += 1
            m.nan_count += len(r.nan_fields)
            for w in r.warnings:
                if "gap" in w:
                    m.gap_events += 1
                elif "oi_surge" in w:
                    m.oi_surges += 1
            for e in r.errors:
                if "breaker" in e.lower() or "circuit" in e.lower():
                    m.breaker_trips += 1
        return m

    def clear(self) -> None:
        self._reports.clear()

"""
MVCCChainStateStore — 多版本并发控制链状态存储

设计：
  - 单写: apply_event() 在写入端（事件循环）串行调用
  - 多读: get_snapshot() 任意线程安全读（无锁，返回不可变快照）
  - GC  : 自动保留最近 N 个版本，防止内存泄漏

兼容 ChainStateStore API（apply_depth, apply_greeks, update_spot）
"""
from __future__ import annotations

import time
import threading
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from ..events.market_events import CleanQuoteEvent, CleanDepthEvent, CleanTradeEvent
from .snapshot import FrozenSnapshot, SnapshotVersion


class MVCCChainStateStore:
    """
    MVCC 版本化链状态存储。

    写入端（事件循环线程）每次调用 apply_* 时生成新版本快照，
    读取端任意时刻调用 get_snapshot() 获取当前最新不可变快照。

    参数:
        keep_versions : GC 保留的历史版本数（默认 3）
    """

    def __init__(self, keep_versions: int = 3) -> None:
        self._keep_versions = keep_versions
        self._version: int = 0
        self._current: Optional[FrozenSnapshot] = None
        self._history: deque[FrozenSnapshot] = deque(maxlen=keep_versions)

        # 可变工作状态（仅写入端访问）
        self._spot_price: float = 0.0
        self._spot_timestamp: float = 0.0
        self._atm_strike: Optional[float] = None
        self._chain: Dict[str, Dict[str, Any]] = {}  # symbol → state dict
        self._nan_count: int = 0
        self._breaker_trips: int = 0

        # 读写锁（snapshot 指针替换为原子操作替代品）
        self._snapshot_lock = threading.Lock()

    # ─────────────────────────────────────────────────────────────────
    #  写入 API
    # ─────────────────────────────────────────────────────────────────

    def update_spot(self, price: float, timestamp: Optional[float] = None) -> None:
        """更新现货价格"""
        self._spot_price = price
        self._spot_timestamp = timestamp or time.monotonic()
        self._commit(seq_no=0, source="spot")

    def apply_depth(self, event: CleanDepthEvent) -> None:
        """应用 L2 深度事件"""
        sym = event.symbol
        entry = self._chain.setdefault(sym, {})
        entry["bid"] = event.bid
        entry["ask"] = event.ask
        entry["bid_size"] = event.bid_size
        entry["ask_size"] = event.ask_size
        self._commit(seq_no=event.seq_no, source="depth")

    def apply_quote(self, event: CleanQuoteEvent) -> None:
        """应用清洁报价事件"""
        sym = event.symbol
        entry = self._chain.setdefault(sym, {})
        entry.update({
            "bid": event.bid, "ask": event.ask, "last": event.last,
            "volume": event.volume, "open_interest": event.open_interest,
            "delta": event.delta, "gamma": event.gamma,
            "theta": event.theta, "vega": event.vega, "iv": event.iv,
            "strike": event.strike, "expiry": event.expiry,
            "option_type": event.option_type,
        })
        self._commit(seq_no=event.seq_no, source="quote")

    def apply_greeks(self, symbol: str, greeks: Dict[str, Any], seq_no: int = 0) -> None:
        """向后兼容：直接写入希腊值（来自 BSM 计算）"""
        entry = self._chain.setdefault(symbol, {})
        entry.update(greeks)
        self._commit(seq_no=seq_no, source="greeks")

    def record_nan(self) -> None:
        self._nan_count += 1

    def record_breaker_trip(self) -> None:
        self._breaker_trips += 1

    # ─────────────────────────────────────────────────────────────────
    #  读取 API（线程安全）
    # ─────────────────────────────────────────────────────────────────

    def get_snapshot(self) -> Tuple[int, Optional[FrozenSnapshot]]:
        """
        返回 (version, snapshot)。

        线程安全：快照为不可变对象，指针读取为原子操作（GIL 保护）。
        """
        snap = self._current
        return (snap.version if snap else 0, snap)

    def get_history(self) -> List[FrozenSnapshot]:
        """返回历史版本列表（按版本号升序）"""
        with self._snapshot_lock:
            return list(self._history)

    # ─────────────────────────────────────────────────────────────────
    #  内部提交
    # ─────────────────────────────────────────────────────────────────

    def _commit(self, seq_no: int, source: str) -> None:
        """创建新版本快照并替换当前快照"""
        self._version += 1
        meta = SnapshotVersion(
            version=self._version,
            created_at=time.monotonic(),
            seq_no=seq_no,
            source=source,
        )
        # 序列化链状态为不可变 tuple
        chain_tuple = tuple(
            (sym, d.get("bid", 0.0), d.get("ask", 0.0),
             d.get("open_interest", 0.0), d.get("delta"))
            for sym, d in self._chain.items()
        )
        snap = FrozenSnapshot(
            version_meta=meta,
            spot_price=self._spot_price,
            spot_timestamp=self._spot_timestamp,
            atm_strike=self._atm_strike,
            chain_snapshot=chain_tuple,
            last_nan_count=self._nan_count,
            last_breaker_trips=self._breaker_trips,
        )

        # 原子替换（GIL 保护下的对象指针赋值）
        old = self._current
        self._current = snap
        if old is not None:
            with self._snapshot_lock:
                self._history.append(old)

        self._gc_old_versions()

    def _gc_old_versions(self) -> None:
        """GC: deque 的 maxlen 已自动限制，此处可扩展为更复杂策略"""
        pass  # deque maxlen 已处理

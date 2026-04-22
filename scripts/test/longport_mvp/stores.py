from __future__ import annotations

from collections import deque

from .extractors import extract_level_price, extract_open_interest, extract_symbol


class TopOfBookCache:
    def __init__(self) -> None:
        self._book: dict[str, tuple[float | None, float | None]] = {}

    def update(self, symbol: str, bids: list[object], asks: list[object]) -> None:
        prev_bid, prev_ask = self._book.get(symbol, (None, None))
        bid1 = extract_level_price(bids)
        ask1 = extract_level_price(asks)
        self._book[symbol] = (prev_bid if bid1 is None else bid1, prev_ask if ask1 is None else ask1)

    def get(self, symbol: str) -> tuple[float | None, float | None]:
        return self._book.get(symbol, (None, None))


class OICache:
    def __init__(self) -> None:
        self._oi: dict[str, tuple[int, float, str]] = {}

    @property
    def size(self) -> int:
        return len(self._oi)

    def update(self, symbol: str, oi: int, *, now_mono: float, source: str) -> None:
        if not symbol or oi <= 0:
            return
        self._oi[symbol] = (oi, now_mono, source)

    def get(self, symbol: str) -> int | None:
        row = self._oi.get(symbol)
        return row[0] if row else None

    def bulk_update_snapshot(self, chain: object, *, now_mono: float) -> int:
        if not isinstance(chain, list):
            return 0
        changed = 0
        for item in chain:
            symbol = extract_symbol(item)
            oi = extract_open_interest(item)
            if symbol is None or oi is None or oi <= 0:
                continue
            prev = self._oi.get(symbol)
            self.update(symbol, oi, now_mono=now_mono, source="snapshot")
            if prev is None or prev[0] != oi:
                changed += 1
        return changed

    def bulk_update_quote_rows(self, rows: object, *, now_mono: float) -> int:
        if not isinstance(rows, list):
            return 0
        changed = 0
        for item in rows:
            symbol = extract_symbol(item)
            oi = extract_open_interest(item)
            if symbol is None or oi is None or oi <= 0:
                continue
            prev = self._oi.get(symbol)
            self.update(symbol, oi, now_mono=now_mono, source="option_quote")
            if prev is None or prev[0] != oi:
                changed += 1
        return changed

    def missing_symbols(self, symbols: set[str], *, now_mono: float, max_age_sec: float) -> list[str]:
        missing: list[str] = []
        for symbol in symbols:
            row = self._oi.get(symbol)
            if row is None or (now_mono - row[1]) > max_age_sec:
                missing.append(symbol)
        return missing


class GreeksCache:
    def __init__(self) -> None:
        self._greeks: dict[str, tuple[float, float, float, str]] = {}
        self.stale_reads = 0

    @property
    def size(self) -> int:
        return len(self._greeks)

    def update(
        self,
        symbol: str,
        *,
        delta: float | None,
        gamma: float | None,
        now_mono: float,
        source: str,
    ) -> None:
        if not symbol:
            return
        self._greeks[symbol] = (float(delta or 0.0), float(gamma or 0.0), now_mono, source)

    def get(self, symbol: str, *, now_mono: float, max_age_sec: float) -> tuple[float, float, bool]:
        row = self._greeks.get(symbol)
        if row is None:
            return 0.0, 0.0, True
        delta, gamma, updated_mono, _ = row
        is_stale = (now_mono - updated_mono) > max_age_sec
        if is_stale:
            self.stale_reads += 1
        return delta, gamma, is_stale

    def bulk_update_snapshot(self, chain: object, *, now_mono: float) -> int:
        if not isinstance(chain, list):
            return 0
        changed = 0
        for item in chain:
            symbol = extract_symbol(item)
            if symbol is None:
                continue
            delta = float((item.get("delta") if isinstance(item, dict) else getattr(item, "delta", 0.0)) or 0.0)
            gamma = float((item.get("gamma") if isinstance(item, dict) else getattr(item, "gamma", 0.0)) or 0.0)
            prev = self._greeks.get(symbol)
            self.update(symbol, delta=delta, gamma=gamma, now_mono=now_mono, source="snapshot")
            if prev is None or prev[0] != delta or prev[1] != gamma:
                changed += 1
        return changed

    def bulk_update_quote_rows(self, rows: object, *, now_mono: float) -> int:
        if not isinstance(rows, list):
            return 0
        changed = 0
        for item in rows:
            symbol = extract_symbol(item)
            if symbol is None:
                continue
            delta = float((item.get("delta") if isinstance(item, dict) else getattr(item, "delta", 0.0)) or 0.0)
            gamma = float((item.get("gamma") if isinstance(item, dict) else getattr(item, "gamma", 0.0)) or 0.0)
            prev = self._greeks.get(symbol)
            self.update(symbol, delta=delta, gamma=gamma, now_mono=now_mono, source="option_quote")
            if prev is None or prev[0] != delta or prev[1] != gamma:
                changed += 1
        return changed


class RecentTradeStore:
    def __init__(self, *, maxlen: int, ttl_sec: float) -> None:
        self._rows: deque[dict[str, object]] = deque(maxlen=maxlen)
        self._ttl_sec = ttl_sec

    @property
    def size(self) -> int:
        return len(self._rows)

    def _trim(self, now_mono: float) -> None:
        threshold = now_mono - self._ttl_sec
        while self._rows and float(self._rows[0].get("timestamp_mono", 0.0) or 0.0) < threshold:
            self._rows.popleft()

    def add(self, row: dict[str, object], *, now_mono: float) -> None:
        self._trim(now_mono)
        self._rows.append(row)

    def cluster_window(self, *, now_mono: float, window_sec: float) -> list[dict[str, object]]:
        self._trim(now_mono)
        threshold = now_mono - window_sec
        return [row for row in self._rows if float(row.get("timestamp_mono", 0.0) or 0.0) >= threshold]

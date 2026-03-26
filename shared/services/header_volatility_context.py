"""Build title-bar volatility context from stable contracts and diagnostics."""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from shared.config import settings

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")
_UTC = timezone.utc


class HeaderVolatilityContextService:
    """Stateful builder for header volatility context.

    This service is intentionally neutral and consumes only stable snapshot
    contracts plus the research feature store.
    """

    def __init__(
        self,
        *,
        research_store: Any,
        lookback_days: int = 20,
        relation_window_seconds: float = 120.0,
        min_history_days: int = 5,
        history_cache_ttl_seconds: float = 60.0,
        history_fetch_count: int = 512,
    ) -> None:
        self._research_store = research_store
        self._lookback_days = lookback_days
        self._relation_window_seconds = relation_window_seconds
        self._min_history_days = min_history_days
        self._history_cache_ttl_seconds = history_cache_ttl_seconds
        self._history_fetch_count = history_fetch_count
        self._relation_history: deque[tuple[float, float, float]] = deque(maxlen=512)
        self._history_cache_trade_date: str | None = None
        self._history_cache_until_mono = 0.0
        self._history_cache_values: list[float] = []

    def build(self, *, snapshot: Any, spot: float, atm_iv: float) -> dict[str, Any]:
        now_mono = time.monotonic()
        current_trade_date = self._current_trade_date(snapshot)
        self._record_relation_point(now_mono=now_mono, spot=spot, atm_iv=atm_iv)
        closes = self._load_completed_day_closes(
            current_trade_date=current_trade_date,
            now_mono=now_mono,
        )
        aux = self._extract_aux(snapshot)
        return {
            "lookback_days": self._lookback_days,
            "lookback_effective_days": len(closes),
            "ivr": self._compute_ivr(current=atm_iv, closes=closes),
            "ivp": self._compute_ivp(current=atm_iv, closes=closes),
            "term_structure": {
                "primary": self._build_term_primary(atm_iv=atm_iv, aux=aux),
                "secondary": self._build_term_secondary(atm_iv=atm_iv, aux=aux),
            },
            "iv_price_relation": self._build_iv_price_relation(),
        }

    def _record_relation_point(self, *, now_mono: float, spot: float, atm_iv: float) -> None:
        spot_value = self._to_positive_float(spot)
        iv_value = self._to_positive_float(atm_iv)
        if spot_value is None or iv_value is None:
            self._prune_relation_history(now_mono)
            return
        self._relation_history.append((now_mono, spot_value, iv_value))
        self._prune_relation_history(now_mono)

    def _prune_relation_history(self, now_mono: float) -> None:
        cutoff = now_mono - self._relation_window_seconds
        while self._relation_history and self._relation_history[0][0] < cutoff:
            self._relation_history.popleft()

    def _load_completed_day_closes(
        self,
        *,
        current_trade_date: str,
        now_mono: float,
    ) -> list[float]:
        if (
            self._history_cache_trade_date == current_trade_date
            and now_mono < self._history_cache_until_mono
        ):
            return list(self._history_cache_values)

        closes: list[tuple[str, datetime, float]] = []
        try:
            rows = self._research_store.latest_feature_view(
                count=self._history_fetch_count,
                view="feature",
                fields=["data_timestamp", "atm_iv"],
            )
        except Exception as exc:
            logger.warning("[HeaderVolatility] latest_feature_view failed: %s", exc)
            rows = []

        per_day: dict[str, tuple[datetime, float]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            timestamp = self._parse_timestamp(row.get("data_timestamp"))
            if timestamp is None:
                continue
            trade_date = timestamp.astimezone(_ET).strftime("%Y-%m-%d")
            if trade_date == current_trade_date:
                continue
            atm_iv = self._to_positive_float(row.get("atm_iv"))
            if atm_iv is None:
                continue
            existing = per_day.get(trade_date)
            if existing is None or timestamp > existing[0]:
                per_day[trade_date] = (timestamp, atm_iv)

        for trade_date, (timestamp, value) in per_day.items():
            closes.append((trade_date, timestamp, value))
        closes.sort(key=lambda item: (item[0], item[1]))

        values = [value for _, _, value in closes][-self._lookback_days :]
        self._history_cache_trade_date = current_trade_date
        self._history_cache_until_mono = now_mono + self._history_cache_ttl_seconds
        self._history_cache_values = list(values)
        return values

    def _compute_ivr(self, *, current: float, closes: list[float]) -> float | None:
        current_value = self._to_positive_float(current)
        if current_value is None or len(closes) < self._min_history_days:
            return None
        min_iv = min(closes)
        max_iv = max(closes)
        span = max_iv - min_iv
        if span <= 1e-9:
            if current_value > max_iv:
                return 100.0
            if current_value < min_iv:
                return 0.0
            return 50.0
        return ((current_value - min_iv) / span) * 100.0

    def _compute_ivp(self, *, current: float, closes: list[float]) -> float | None:
        current_value = self._to_positive_float(current)
        if current_value is None or len(closes) < self._min_history_days:
            return None
        lower_days = sum(1 for value in closes if value < current_value)
        return (lower_days / len(closes)) * 100.0

    def _build_term_primary(self, *, atm_iv: float, aux: dict[str, Any]) -> dict[str, Any]:
        anchor_iv = self._to_positive_float(aux.get("atm_iv_1dte"))
        ratio = self._safe_ratio(atm_iv, anchor_iv)
        return {
            "anchor": "1DTE",
            "symbol": "SPY.US",
            "expiry": aux.get("next_expiry"),
            "iv": anchor_iv,
            "ratio": ratio,
            "state": self._term_state(ratio),
        }

    def _build_term_secondary(self, *, atm_iv: float, aux: dict[str, Any]) -> dict[str, Any]:
        vix_iv = self._to_positive_float(aux.get("vix_iv_decimal"))
        ratio = self._safe_ratio(atm_iv, vix_iv)
        return {
            "anchor": ".VIX.US",
            "symbol": ".VIX.US",
            "iv_decimal": vix_iv,
            "ratio": ratio,
            "state": self._term_state(ratio),
        }

    def _build_iv_price_relation(self) -> dict[str, Any]:
        if len(self._relation_history) < 2:
            return self._empty_relation()

        oldest = self._relation_history[0]
        newest = self._relation_history[-1]
        if oldest[1] <= 0.0:
            return self._empty_relation()

        price_change_pct = ((newest[1] - oldest[1]) / oldest[1]) * 100.0
        iv_change_pp = (newest[2] - oldest[2]) * 100.0
        spot_threshold = max(0.0, float(settings.spot_roc_threshold_pct))
        iv_threshold = max(0.0, float(settings.iv_roc_threshold_pct))
        price_sig = abs(price_change_pct) >= spot_threshold
        iv_sig = abs(iv_change_pp) >= iv_threshold

        state = "UNAVAILABLE"
        if price_sig and iv_sig:
            same_sign = math.copysign(1.0, price_change_pct) == math.copysign(1.0, iv_change_pp)
            state = "POSITIVE_DIVERGENCE" if same_sign else "INVERSE_CONFIRM"
        elif iv_sig:
            state = "VOL_LEAD"
        elif price_sig:
            state = "PRICE_LEAD"

        beta = None
        if abs(price_change_pct) >= 1e-9:
            beta = iv_change_pp / abs(price_change_pct)

        return {
            "window_seconds": int(self._relation_window_seconds),
            "iv_change_pp": iv_change_pp,
            "price_change_pct": price_change_pct,
            "beta_pp_per_pct": beta,
            "state": state,
        }

    @staticmethod
    def _empty_relation() -> dict[str, Any]:
        return {
            "window_seconds": 120,
            "iv_change_pp": None,
            "price_change_pct": None,
            "beta_pp_per_pct": None,
            "state": "UNAVAILABLE",
        }

    def _extract_aux(self, snapshot: Any) -> dict[str, Any]:
        metadata = self._get(snapshot, "extra_metadata", {})
        if isinstance(metadata, dict):
            aux = metadata.get("header_volatility_aux", {})
            if isinstance(aux, dict):
                return aux
        if isinstance(snapshot, dict):
            aux = snapshot.get("header_volatility_aux_diagnostics", {})
            if isinstance(aux, dict):
                return aux
        return {}

    def _current_trade_date(self, snapshot: Any) -> str:
        metadata = self._get(snapshot, "extra_metadata", {})
        raw = None
        if isinstance(metadata, dict):
            raw = metadata.get("source_data_timestamp_utc")
        if raw is None:
            raw = self._get(snapshot, "computed_at", None)
        ts = self._parse_timestamp(raw)
        if ts is None:
            ts = datetime.now(_UTC)
        return ts.astimezone(_ET).strftime("%Y-%m-%d")

    @staticmethod
    def _term_state(ratio: float | None) -> str:
        if ratio is None:
            return "UNAVAILABLE"
        if ratio > 1.05:
            return "INVERTED"
        if ratio >= 0.95:
            return "FLAT"
        return "NORMAL"

    @staticmethod
    def _safe_ratio(current: float, anchor: float | None) -> float | None:
        current_value = HeaderVolatilityContextService._to_positive_float(current)
        if current_value is None or anchor is None:
            return None
        if anchor <= 0.0:
            return None
        return current_value / anchor

    @staticmethod
    def _get(obj: Any, name: str, default: Any = None) -> Any:
        if hasattr(obj, name):
            return getattr(obj, name)
        if isinstance(obj, dict):
            return obj.get(name, default)
        return default

    @staticmethod
    def _to_positive_float(raw: Any) -> float | None:
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value) or value <= 0.0:
            return None
        return value

    @staticmethod
    def _parse_timestamp(raw: Any) -> datetime | None:
        if isinstance(raw, datetime):
            dt = raw
        elif isinstance(raw, str):
            text = raw.strip()
            if not text:
                return None
            if text.endswith("Z"):
                text = f"{text[:-1]}+00:00"
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                return None
        else:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=_UTC)
        return dt.astimezone(_UTC)

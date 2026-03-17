"""Skew and RR25 themed feature extractors."""

from __future__ import annotations

import logging
import math
from typing import Any

from l2_decision.feature_store.extractors_common import _get_agg, _get_val

logger = logging.getLogger(__name__)

IV_PERCENT_UPPER_BOUND = 300.0
IV_PERCENT_SWITCH = 3.0
DELTA_PERCENT_UPPER_BOUND = 100.0


class _Skew25dMetricsExtractor:
    """Compute true 25-delta skew and validity from L1/L2 snapshot contracts."""

    _CALL_TARGET_DELTA: float = 0.25
    _PUT_TARGET_DELTA: float = -0.25
    _DEFAULT_DELTA_TOLERANCE: float = 0.10

    def __init__(self, delta_tolerance: float = _DEFAULT_DELTA_TOLERANCE) -> None:
        self._delta_tolerance = abs(float(delta_tolerance))
        self._last_key: tuple[int, int | None, int] | None = None
        self._last_value: float = 0.0
        self._last_valid: float = 0.0
        self._last_rr25: float = 0.0

    def extract_value(self, snapshot: Any) -> float:
        value, _, _ = self._compute(snapshot)
        return value

    def extract_rr25(self, snapshot: Any) -> float:
        _, _, rr25 = self._compute(snapshot)
        return rr25

    def extract_valid(self, snapshot: Any) -> float:
        _, valid, _ = self._compute(snapshot)
        return valid

    def reset(self) -> None:
        self._last_key = None
        self._last_value = 0.0
        self._last_valid = 0.0
        self._last_rr25 = 0.0

    def _compute(self, snapshot: Any) -> tuple[float, float, float]:
        key = self._build_cache_key(snapshot)
        if key is not None and key == self._last_key:
            return self._last_value, self._last_valid, self._last_rr25

        value, valid, rr25 = self._compute_uncached(snapshot)
        if key is not None:
            self._last_key = key
            self._last_value = value
            self._last_valid = valid
            self._last_rr25 = rr25
        return value, valid, rr25

    def _compute_uncached(self, snapshot: Any) -> tuple[float, float, float]:
        rows, atm_iv = self._prepare_rows_and_atm(snapshot)
        if rows is None or atm_iv is None:
            return 0.0, 0.0, 0.0

        call_match, put_match = self._find_best_leg_matches(rows)
        if call_match is None or put_match is None:
            return 0.0, 0.0, 0.0
        if call_match[0] > self._delta_tolerance or put_match[0] > self._delta_tolerance:
            return 0.0, 0.0, 0.0

        return self._finalize_metrics(atm_iv, call_match, put_match)

    def _prepare_rows_and_atm(self, snapshot: Any) -> tuple[list[dict[str, Any]] | None, float | None]:
        chain = _get_val(snapshot, "chain")
        atm_iv = self._normalize_iv(_get_agg(snapshot, "atm_iv"))
        if chain is None or atm_iv is None or atm_iv <= 0.0:
            return None, None

        rows = self._coerce_chain_rows(chain)
        if not rows:
            return None, None
        return rows, atm_iv

    def _find_best_leg_matches(
        self,
        rows: list[dict[str, Any]],
    ) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
        call_match: tuple[float, float] | None = None
        put_match: tuple[float, float] | None = None

        for row in rows:
            candidate = self._extract_leg_candidate(row)
            if candidate is None:
                continue

            is_call, distance, iv = candidate

            if is_call:
                if call_match is None or distance < call_match[0]:
                    call_match = (distance, iv)
            else:
                if put_match is None or distance < put_match[0]:
                    put_match = (distance, iv)
        return call_match, put_match

    def _extract_leg_candidate(self, row: dict[str, Any]) -> tuple[bool, float, float] | None:
        is_call = self._extract_is_call(row)
        if is_call is None:
            return None

        iv = self._extract_iv(row)
        if iv is None:
            return None

        delta = self._extract_delta(row, is_call=is_call)
        if delta is None:
            return None

        target = self._CALL_TARGET_DELTA if is_call else self._PUT_TARGET_DELTA
        distance = abs(delta - target)
        if not math.isfinite(distance):
            return None
        return is_call, distance, iv

    @staticmethod
    def _finalize_metrics(
        atm_iv: float,
        call_match: tuple[float, float],
        put_match: tuple[float, float],
    ) -> tuple[float, float, float]:
        skew = (put_match[1] - call_match[1]) / atm_iv
        rr25 = call_match[1] - put_match[1]
        if not math.isfinite(skew):
            return 0.0, 0.0, 0.0
        if not math.isfinite(rr25):
            rr25 = 0.0
        return max(-1.0, min(1.0, skew)), 1.0, rr25

    @staticmethod
    def _build_cache_key(snapshot: Any) -> tuple[int, int | None, int] | None:
        chain = _get_val(snapshot, "chain")
        if chain is None:
            return None
        raw_version = getattr(snapshot, "version", None)
        if raw_version is None and isinstance(snapshot, dict):
            raw_version = snapshot.get("version")
        version = _Skew25dMetricsExtractor._coerce_version_token(raw_version)
        return (id(snapshot), version, id(chain))

    @staticmethod
    def _coerce_version_token(raw_version: Any) -> int | None:
        if isinstance(raw_version, bool):
            return None
        if isinstance(raw_version, int):
            return raw_version
        if isinstance(raw_version, float):
            return int(raw_version) if math.isfinite(raw_version) else None
        if isinstance(raw_version, str):
            text = raw_version.strip()
            return int(text) if text.isdigit() else None
        return None

    @staticmethod
    def _coerce_chain_rows(chain: Any) -> list[dict[str, Any]]:
        recordbatch_rows = _Skew25dMetricsExtractor._coerce_recordbatch_rows(chain)
        if recordbatch_rows is not None:
            return recordbatch_rows
        return _Skew25dMetricsExtractor._coerce_iterable_rows(chain)

    @staticmethod
    def _coerce_recordbatch_rows(chain: Any) -> list[dict[str, Any]] | None:
        try:
            import pyarrow as pa
        except Exception as exc:
            logger.debug("pyarrow import unavailable for skew extractor: %s", exc)
            return None

        if not isinstance(chain, pa.RecordBatch):
            return None

        try:
            rows = chain.to_pylist()
        except Exception as exc:
            logger.debug("recordbatch to_pylist failed for skew extractor: %s", exc)
            return []
        return [row for row in rows if isinstance(row, dict)]

    @staticmethod
    def _coerce_iterable_rows(chain: Any) -> list[dict[str, Any]]:
        if isinstance(chain, (str, bytes)):
            return []
        if isinstance(chain, dict):
            return []
        try:
            rows = list(chain)
        except TypeError:
            return []
        return [row for row in rows if isinstance(row, dict)]

    @staticmethod
    def _extract_is_call(row: dict[str, Any]) -> bool | None:
        raw_is_call = row.get("is_call")
        if isinstance(raw_is_call, bool):
            return raw_is_call

        raw_type = row.get("option_type", row.get("type"))
        text = str(raw_type).strip().upper()
        if text in ("CALL", "C"):
            return True
        if text in ("PUT", "P"):
            return False
        return None

    @classmethod
    def _extract_iv(cls, row: dict[str, Any]) -> float | None:
        for key in ("computed_iv", "iv", "implied_volatility"):
            iv = cls._normalize_iv(row.get(key))
            if iv is not None and iv > 0.0:
                return iv
        return None

    @classmethod
    def _extract_delta(cls, row: dict[str, Any], *, is_call: bool) -> float | None:
        for key in ("computed_delta", "delta"):
            raw = row.get(key)
            if raw is None:
                continue
            normalized = cls._normalize_delta(raw)
            if normalized is None:
                continue
            return cls._align_delta_sign(normalized, is_call=is_call)
        return None

    @staticmethod
    def _normalize_delta(raw: Any) -> float | None:
        try:
            delta = float(raw)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(delta):
            return None
        if abs(delta) > 1.0 and abs(delta) <= DELTA_PERCENT_UPPER_BOUND:
            delta = delta / DELTA_PERCENT_UPPER_BOUND
        if abs(delta) > 1.0:
            return None
        return delta

    @staticmethod
    def _align_delta_sign(delta: float, *, is_call: bool) -> float:
        if is_call and delta < 0:
            return abs(delta)
        if (not is_call) and delta > 0:
            return -delta
        return delta

    @staticmethod
    def _normalize_iv(value: Any) -> float | None:
        try:
            iv = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(iv):
            return None
        if iv > IV_PERCENT_SWITCH and iv <= IV_PERCENT_UPPER_BOUND:
            iv = iv / DELTA_PERCENT_UPPER_BOUND
        if iv <= 0.0:
            return None
        return iv


class _Skew25dExtractor:
    """Return normalized true 25-delta skew value."""

    def __init__(self, metrics: _Skew25dMetricsExtractor) -> None:
        self._metrics = metrics

    def __call__(self, snapshot: Any) -> float:
        return self._metrics.extract_value(snapshot)

    def reset(self) -> None:
        self._metrics.reset()


class _Skew25dValidExtractor:
    """Return validity flag (1.0/0.0) for true 25-delta skew."""

    def __init__(self, metrics: _Skew25dMetricsExtractor) -> None:
        self._metrics = metrics

    def __call__(self, snapshot: Any) -> float:
        return self._metrics.extract_valid(snapshot)

    def reset(self) -> None:
        self._metrics.reset()


class _RR25CallMinusPutExtractor:
    """Return canonical 25-delta risk reversal: call IV minus put IV."""

    def __init__(self, metrics: _Skew25dMetricsExtractor) -> None:
        self._metrics = metrics

    def __call__(self, snapshot: Any) -> float:
        return self._metrics.extract_rr25(snapshot)

    def reset(self) -> None:
        self._metrics.reset()

"""L1-priority input adapter for Active Options runtime snapshots.

This module is cross-layer neutral (shared service). It fuses L1 and L0 chain
rows with L1-computed fields as priority sources, then emits a normalized
snapshot contract for app loops to publish into shared state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import math
from typing import Any, Mapping

logger = logging.getLogger(__name__)


ACTIVE_OPTIONS_INPUT_REASON_EMPTY_CHAIN = "empty_chain"
ACTIVE_OPTIONS_INPUT_REASON_INVALID_SPOT = "invalid_spot"

_KEY_STRIKE_ROUND_DIGITS = 4
_OPTION_TYPE_CALL = "CALL"
_OPTION_TYPE_PUT = "PUT"


@dataclass(frozen=True)
class ActiveOptionsInputSnapshotData:
    """Normalized cross-layer-safe Active Options input snapshot."""

    chain: list[dict[str, Any]] = field(default_factory=list)
    spot: float = 0.0
    atm_iv: float = 0.0
    ttm_seconds: float | None = None
    source_version: int = 0
    source_timestamp_utc: str | None = None
    valid: bool = False
    invalid_reason: str | None = None


def build_active_options_input_snapshot(
    *,
    l0_snapshot: Mapping[str, Any],
    l1_snapshot: Any,
) -> ActiveOptionsInputSnapshotData:
    """Build one L1-priority fused ActiveOptions input snapshot."""
    l0_rows = _extract_chain_rows_from_l0(l0_snapshot)
    l1_rows = _extract_chain_rows_from_l1(l1_snapshot)
    merged_rows = _merge_l1_priority_rows(l0_rows=l0_rows, l1_rows=l1_rows)

    spot = _resolve_spot(l0_snapshot=l0_snapshot, l1_snapshot=l1_snapshot)
    atm_iv = _resolve_atm_iv(l0_snapshot=l0_snapshot, l1_snapshot=l1_snapshot)
    ttm_seconds = _resolve_ttm_seconds(l0_snapshot=l0_snapshot, l1_snapshot=l1_snapshot)
    source_version = _resolve_source_version(l0_snapshot=l0_snapshot, l1_snapshot=l1_snapshot)
    source_timestamp_utc = _resolve_source_timestamp_utc(l0_snapshot=l0_snapshot)
    valid, invalid_reason = _evaluate_validity(chain=merged_rows, spot=spot)
    logger.debug(
        "[ActiveOptionsInput] source_version=%s source_ts=%s valid=%s chain_rows=%d "
        "promoted_gamma=%d promoted_vanna=%d promoted_iv=%d promoted_delta=%d spot=%.4f atm_iv=%.4f",
        source_version,
        source_timestamp_utc,
        valid,
        len(merged_rows),
        _count_promoted_field(merged_rows, "computed_gamma", "gamma"),
        _count_promoted_field(merged_rows, "computed_vanna", "vanna"),
        _count_promoted_field(merged_rows, "computed_iv", "implied_volatility"),
        _count_promoted_field(merged_rows, "computed_delta", "delta"),
        spot,
        atm_iv,
    )

    return ActiveOptionsInputSnapshotData(
        chain=merged_rows,
        spot=spot,
        atm_iv=atm_iv,
        ttm_seconds=ttm_seconds,
        source_version=source_version,
        source_timestamp_utc=source_timestamp_utc,
        valid=valid,
        invalid_reason=invalid_reason,
    )


def _extract_chain_rows_from_l0(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_chain = snapshot.get("chain")
    if not isinstance(raw_chain, list):
        return []
    return [dict(row) for row in raw_chain if isinstance(row, dict)]


def _extract_chain_rows_from_l1(l1_snapshot: Any) -> list[dict[str, Any]]:
    if l1_snapshot is None:
        return []
    chain = getattr(l1_snapshot, "chain", None)
    if chain is None and isinstance(l1_snapshot, Mapping):
        chain = l1_snapshot.get("chain")
    return _normalize_chain_rows(chain)


def _normalize_chain_rows(chain: Any) -> list[dict[str, Any]]:
    if isinstance(chain, list):
        return [dict(row) for row in chain if isinstance(row, dict)]
    if hasattr(chain, "to_pylist") and callable(chain.to_pylist):
        try:
            py_rows = chain.to_pylist()
        except Exception:
            return []
        if not isinstance(py_rows, list):
            return []
        return [dict(row) for row in py_rows if isinstance(row, dict)]
    return []


def _merge_l1_priority_rows(
    *,
    l0_rows: list[dict[str, Any]],
    l1_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not l0_rows:
        return [_apply_l1_priority_fields(dict(row)) for row in l1_rows]
    if not l1_rows:
        return [dict(row) for row in l0_rows]

    l1_by_key: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(l1_rows):
        l1_by_key[_row_key(row, idx)] = row

    merged: list[dict[str, Any]] = []
    used_l1_keys: set[str] = set()
    for idx, l0_row in enumerate(l0_rows):
        key = _row_key(l0_row, idx)
        l1_row = l1_by_key.get(key)
        if l1_row is None:
            merged.append(dict(l0_row))
            continue
        used_l1_keys.add(key)
        merged.append(_merge_one_row(l0_row=l0_row, l1_row=l1_row))

    for idx, l1_row in enumerate(l1_rows):
        key = _row_key(l1_row, idx)
        if key in used_l1_keys:
            continue
        merged.append(_apply_l1_priority_fields(dict(l1_row)))
    return merged


def _merge_one_row(
    *,
    l0_row: dict[str, Any],
    l1_row: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(l0_row)
    for key, value in l1_row.items():
        if _is_missing(value):
            continue
        merged[key] = value
    return _apply_l1_priority_fields(merged)


def _apply_l1_priority_fields(row: dict[str, Any]) -> dict[str, Any]:
    _promote_computed_field(row, "computed_iv", ("implied_volatility", "iv"))
    _promote_computed_field(row, "computed_gamma", ("gamma",))
    _promote_computed_field(row, "computed_vanna", ("vanna",))
    _promote_computed_field(row, "computed_delta", ("delta",))
    return row


def _promote_computed_field(
    row: dict[str, Any],
    computed_key: str,
    aliases: tuple[str, ...],
) -> None:
    raw = row.get(computed_key)
    if _is_missing(raw):
        return
    for alias in aliases:
        row[alias] = raw


def _row_key(row: dict[str, Any], idx: int) -> str:
    symbol = str(row.get("symbol", "")).strip().upper()
    if symbol:
        return symbol
    option_type = _normalize_option_type(row)
    strike = _to_non_negative_float(row.get("strike"))
    if strike <= 0.0:
        strike = _to_non_negative_float(row.get("strike_price"))
    return f"fallback:{idx}:{option_type}:{round(strike, _KEY_STRIKE_ROUND_DIGITS)}"


def _normalize_option_type(row: dict[str, Any]) -> str:
    token = str(row.get("option_type") or row.get("type") or "").strip().upper()
    if token in {"CALL", "C"}:
        return _OPTION_TYPE_CALL
    if token in {"PUT", "P"}:
        return _OPTION_TYPE_PUT
    return _OPTION_TYPE_CALL if bool(row.get("is_call")) else _OPTION_TYPE_PUT


def _resolve_spot(*, l0_snapshot: Mapping[str, Any], l1_snapshot: Any) -> float:
    l1_spot = _to_non_negative_float(getattr(l1_snapshot, "spot", None))
    if l1_spot > 0.0:
        return l1_spot
    return _to_non_negative_float(l0_snapshot.get("spot"))


def _resolve_atm_iv(*, l0_snapshot: Mapping[str, Any], l1_snapshot: Any) -> float:
    l1_aggregates = getattr(l1_snapshot, "aggregates", None)
    l1_atm_iv = _to_non_negative_float(getattr(l1_aggregates, "atm_iv", None))
    if l1_atm_iv > 0.0:
        return l1_atm_iv
    return 0.0


def _resolve_ttm_seconds(*, l0_snapshot: Mapping[str, Any], l1_snapshot: Any) -> float | None:
    l1_ttm_seconds = _to_non_negative_float(getattr(l1_snapshot, "ttm_seconds", None))
    if l1_ttm_seconds > 0.0:
        return l1_ttm_seconds
    return None


def _resolve_source_version(*, l0_snapshot: Mapping[str, Any], l1_snapshot: Any) -> int:
    l1_version = _to_non_negative_int(getattr(l1_snapshot, "version", None))
    if l1_version > 0:
        return l1_version
    return _to_non_negative_int(l0_snapshot.get("version"))


def _resolve_source_timestamp_utc(*, l0_snapshot: Mapping[str, Any]) -> str | None:
    raw = l0_snapshot.get("as_of_utc")
    if raw is None:
        raw = l0_snapshot.get("as_of")
    dt = _coerce_utc_datetime(raw)
    if dt is None:
        return None
    return dt.isoformat()


def _evaluate_validity(
    *,
    chain: list[dict[str, Any]],
    spot: float,
) -> tuple[bool, str | None]:
    if not chain:
        return False, ACTIVE_OPTIONS_INPUT_REASON_EMPTY_CHAIN
    if spot <= 0.0:
        return False, ACTIVE_OPTIONS_INPUT_REASON_INVALID_SPOT
    return True, None


def _count_promoted_field(
    rows: list[dict[str, Any]],
    computed_key: str,
    alias_key: str,
) -> int:
    count = 0
    for row in rows:
        if _is_missing(row.get(computed_key)) or _is_missing(row.get(alias_key)):
            continue
        if row.get(computed_key) == row.get(alias_key):
            count += 1
    return count


def _to_non_negative_float(raw: Any) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value) or value < 0.0:
        return 0.0
    return value


def _to_non_negative_int(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    if value < 0:
        return 0
    return value


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _coerce_utc_datetime(raw: Any) -> datetime | None:
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
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

"""Fallback helpers for ActiveOptionsRuntimeService."""

from __future__ import annotations

from shared_rust.models import FlowEngineOutput
from . import runtime_service_support as support
from .constants import ACTIVE_OPTIONS_SIGNATURE_STRIKE_ROUND_DIGITS


def _signature_from_row(row: dict[str, object]) -> tuple[str, str, float]:
    normalized = support.normalize_chain_volume_fields(row)
    return (
        str(normalized.get("symbol", "")),
        str(normalized.get("option_type", "CALL")).upper(),
        round(float(support._to_float(normalized.get("strike"), 0.0)), ACTIVE_OPTIONS_SIGNATURE_STRIKE_ROUND_DIGITS),
    )


def _with_synthetic_volume_for_fallback(
    row: dict[str, object],
    *,
    force_minimum: bool = False,
) -> dict[str, object]:
    out = dict(row)
    volume = support._to_int(out.get("volume"), 0)
    if volume > 0:
        return out

    turnover = support._to_float(out.get("turnover"), 0.0)
    if turnover <= 0.0:
        if support._to_int(out.get("open_interest"), 0) > 0:
            out["volume"] = 1
        elif force_minimum:
            out["volume"] = 1
        return out

    last_price = support._to_float(out.get("last_price"), 0.0)
    if last_price > 0.0:
        inferred = int(turnover / max(1e-6, last_price * 100.0))
        out["volume"] = max(1, inferred)
        return out

    out["volume"] = 1
    return out


def _rank_rows_by_volume(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (
            -support._to_int(row.get("volume"), 0),
            -support._to_float(row.get("turnover"), 0.0),
            -support._to_int(row.get("open_interest"), 0),
            str(row.get("symbol", "")),
            support._to_float(row.get("strike"), 0.0),
            str(row.get("option_type", row.get("type", ""))),
        ),
    )


def _prefer_positive_volume_candidates(
    normalized: list[dict[str, object]],
    *,
    target: int,
) -> tuple[list[dict[str, object]], str | None]:
    if target <= 0:
        return [], None
    positive_volume_rows = [
        row for row in normalized if support._to_int(row.get("volume"), 0) > 0
    ]
    if not positive_volume_rows:
        return [], None
    return (
        _rank_rows_by_volume(positive_volume_rows)[:target],
        support.FALLBACK_REASON_SUBTHRESHOLD_VOLUME,
    )


def fallback_candidates_when_empty(
    *,
    chain: list[dict[str, object]],
    max_candidates: int,
) -> tuple[list[dict[str, object]], str]:
    """Build fallback candidates when min-volume filter returns empty."""
    target = max(0, int(max_candidates))
    if target == 0:
        return [], "none"

    normalized = [support.normalize_chain_volume_fields(option_row) for option_row in chain]
    preferred_rows, preferred_mode = _prefer_positive_volume_candidates(
        normalized,
        target=target,
    )
    if preferred_rows:
        return preferred_rows, str(preferred_mode or "none")

    eligible = [
        row
        for row in normalized
        if support._to_float(row.get("turnover"), 0.0) > 0.0
        or support._to_int(row.get("open_interest"), 0) > 0
    ]
    if eligible:
        ranked = sorted(
            eligible,
            key=lambda row: (
                -support._to_float(row.get("turnover"), 0.0),
                -support._to_int(row.get("open_interest"), 0),
                str(row.get("symbol", "")),
                support._to_float(row.get("strike"), 0.0),
                str(row.get("option_type", row.get("type", ""))),
            ),
        )
        candidates = ranked[:target]
        return (
            [_with_synthetic_volume_for_fallback(row) for row in candidates],
            "turnover_open_interest",
        )

    if not normalized:
        return [], "none"

    ranked_hard = sorted(
        normalized,
        key=lambda row: (
            -support._to_int(row.get("volume"), 0),
            -support._to_int(row.get("open_interest"), 0),
            -support._to_float(row.get("turnover"), 0.0),
            -support._to_float(row.get("last_price"), 0.0),
            str(row.get("symbol", "")),
            support._to_float(row.get("strike"), 0.0),
            str(row.get("option_type", row.get("type", ""))),
        ),
    )
    candidates = ranked_hard[:target]
    return (
        [_with_synthetic_volume_for_fallback(row, force_minimum=True) for row in candidates],
        "hard_chain",
    )


def supplement_partial_candidates(
    *,
    filtered: list[dict[str, object]],
    chain: list[dict[str, object]],
    target_limit: int,
) -> tuple[list[dict[str, object]], str | None, set[tuple[str, str, float]]]:
    """Supplement filtered rows up to target_limit using existing fallback ranking."""
    missing = max(0, int(target_limit) - len(filtered))
    if missing <= 0:
        return list(filtered), None, set()

    existing = {_signature_from_row(row) for row in filtered}
    remainder = [row for row in chain if _signature_from_row(row) not in existing]
    fallback_rows, fallback_mode = fallback_candidates_when_empty(chain=remainder, max_candidates=missing)
    supplemented: list[dict[str, object]] = list(filtered)
    added_signatures: set[tuple[str, str, float]] = set()
    for row in fallback_rows:
        signature = _signature_from_row(row)
        if signature in existing or signature in added_signatures:
            continue
        supplemented.append(row)
        added_signatures.add(signature)
        if len(added_signatures) >= missing:
            break
    resolved_mode = fallback_mode if added_signatures else None
    return supplemented, resolved_mode, added_signatures


def build_neutral_outputs_from_chain(
    *,
    filtered: list[dict[str, object]],
    limit: int,
) -> list[FlowEngineOutput]:
    target = max(0, int(limit))
    if target <= 0 or not filtered:
        return []

    ranked = sorted(
        filtered,
        key=lambda row: (
            -support._to_int(row.get("volume"), 0),
            -support._to_float(row.get("turnover"), 0.0),
            -support._to_int(row.get("open_interest"), 0),
            str(row.get("symbol", "")),
            support._to_float(row.get("strike"), 0.0),
            str(row.get("option_type", row.get("type", ""))),
        ),
    )[:target]

    outputs: list[FlowEngineOutput] = []
    for row in ranked:
        option_type = str(row.get("option_type", "CALL")).strip().upper()
        if option_type not in {"CALL", "PUT"}:
            option_type = "CALL" if bool(row.get("is_call")) else "PUT"
        outputs.append(
            FlowEngineOutput(
                symbol=str(row.get("symbol", "SPY")),
                option_type=option_type,
                strike=float(support._to_float(row.get("strike"), 0.0)),
                implied_volatility=float(support._to_float(row.get("implied_volatility"), 0.0)),
                volume=max(0, support._to_int(row.get("volume"), 0)),
                turnover=max(0.0, support._to_float(row.get("turnover"), 0.0)),
                flow_d=0.0,
                flow_e=0.0,
                flow_g=0.0,
                flow_d_z=0.0,
                flow_e_z=0.0,
                flow_g_z=0.0,
                flow_deg=0.0,
                impact_index=0.0,
                is_sweep=False,
                flow_direction="NEUTRAL",
                flow_intensity="LOW",
                engine_d_active=False,
                engine_e_active=False,
                engine_g_active=False,
            )
        )
    return outputs


def mark_rows_with_fallback_signatures(
    rows: list[dict[str, object]],
    *,
    fallback_reason: str,
    signatures: set[tuple[str, str, float]],
) -> list[dict[str, object]]:
    """Mark only selected real rows as synthetic fallback rows."""
    if not signatures:
        return rows

    tagged: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        if bool(updated.get("is_placeholder", False)):
            tagged.append(updated)
            continue
        signature = (
            str(updated.get("contract_symbol", updated.get("symbol", ""))),
            str(updated.get("option_type", "CALL")).upper(),
            round(float(support._to_float(updated.get("strike"), 0.0)), ACTIVE_OPTIONS_SIGNATURE_STRIKE_ROUND_DIGITS),
        )
        if signature in signatures:
            updated["fallback_reason"] = fallback_reason
            if fallback_reason == support.FALLBACK_REASON_SUBTHRESHOLD_VOLUME:
                updated["row_quality"] = support.ROW_QUALITY_REAL
                updated["is_synthetic_fallback"] = False
            else:
                updated["row_quality"] = support.ROW_QUALITY_FALLBACK_SYNTHETIC
                updated["is_synthetic_fallback"] = True
                updated["flow_signal_state"] = support.ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED
                if support._is_missing(updated.get("flow_signal_reason")):
                    updated["flow_signal_reason"] = fallback_reason
        tagged.append(updated)
    return tagged


def mark_real_rows_with_fallback_reason(
    rows: list[dict[str, object]],
    *,
    fallback_reason: str,
) -> list[dict[str, object]]:
    tagged: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        if bool(updated.get("is_placeholder", False)):
            tagged.append(updated)
            continue
        updated["fallback_reason"] = fallback_reason
        if fallback_reason == support.FALLBACK_REASON_SUBTHRESHOLD_VOLUME:
            updated["row_quality"] = support.ROW_QUALITY_REAL
            updated["is_synthetic_fallback"] = False
        else:
            updated["row_quality"] = support.ROW_QUALITY_FALLBACK_SYNTHETIC
            updated["is_synthetic_fallback"] = True
            updated["flow_signal_state"] = support.ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED
            if support._is_missing(updated.get("flow_signal_reason")):
                updated["flow_signal_reason"] = fallback_reason
        tagged.append(updated)
    return tagged

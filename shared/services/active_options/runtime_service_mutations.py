"""State and fallback mutation helpers for ActiveOptionsRuntimeService."""

from __future__ import annotations

import logging
from typing import Any

from shared.config import settings
from shared.models.flow_engine import FlowEngineOutput
from . import runtime_service_fallbacks as fallback_support
from . import runtime_service_support as support

logger = logging.getLogger(__name__)


def reset_cache_state(service: Any) -> None:
    service._latest_payload = []
    service._latest_signature = None
    service._pending_signature = None
    service._pending_rows = []
    service._pending_hits = 0


def clear_pending_state(service: Any) -> None:
    service._pending_signature = None
    service._pending_rows = []
    service._pending_hits = 0


def apply_zero_limit_guard(service: Any, target_limit: int) -> bool:
    if target_limit > 0:
        return False
    reset_cache_state(service)
    return True


def resolve_empty_filter_fallback(
    service: Any,
    *,
    filtered: list[dict[str, Any]],
    chain: list[dict[str, Any]],
    target_limit: int,
    effective_max_candidates: int,
    fallback_enabled: bool,
) -> tuple[list[dict[str, Any]], str | None]:
    if filtered or target_limit <= 0 or effective_max_candidates <= 0:
        return filtered, None
    if not fallback_enabled and chain:
        logger.warning(
            "[ActiveOptionsRuntimeService] empty-filter fallback disabled by config but chain is non-empty; "
            "forcing hard fallback for continuity chain_size=%d",
            len(chain),
        )

    fallback_candidates, fallback_mode = fallback_support.fallback_candidates_when_empty(
        chain=chain,
        max_candidates=effective_max_candidates,
    )
    if not fallback_candidates:
        return filtered, None

    service._empty_filter_fallback_count += 1
    service._last_empty_filter_fallback_at_utc = service._utc_now_iso()
    threshold = int(getattr(settings, "flow_active_min_volume", 100) or 100)
    if fallback_mode == support.FALLBACK_REASON_HARD_CHAIN:
        logger.warning(
            "[ActiveOptionsRuntimeService] No options above min_volume threshold — "
            "using hard fallback from non-empty chain candidates=%d chain_size=%d threshold=%d",
            len(fallback_candidates),
            len(chain),
            threshold,
        )
    else:
        logger.warning(
            "[ActiveOptionsRuntimeService] No options above min_volume threshold — "
            "using turnover/open_interest fallback candidates=%d threshold=%d",
            len(fallback_candidates),
            threshold,
        )
    resolved_mode = str(fallback_mode).strip() if fallback_mode is not None else None
    return fallback_candidates, resolved_mode


def resolve_partial_filter_fallback(
    service: Any,
    *,
    filtered: list[dict[str, Any]],
    chain: list[dict[str, Any]],
    target_limit: int,
) -> tuple[list[dict[str, Any]], str | None, set[tuple[str, str, float]]]:
    service._last_supplemented_rows = 0
    service._last_partial_fallback_mode = None
    if target_limit <= 0 or not filtered or len(filtered) >= target_limit:
        return filtered, None, set()

    supplemented, fallback_mode, added_signatures = fallback_support.supplement_partial_candidates(
        filtered=filtered,
        chain=chain,
        target_limit=target_limit,
    )
    if not added_signatures:
        return supplemented, None, set()

    service._partial_fallback_count += 1
    service._last_partial_fallback_at_utc = service._utc_now_iso()
    service._last_partial_fallback_mode = fallback_mode
    service._last_supplemented_rows = len(added_signatures)
    logger.warning(
        "[ActiveOptionsRuntimeService] Partial fallback supplemented sparse filtered candidates=%d "
        "supplemented=%d chain_size=%d threshold=%d mode=%s",
        len(filtered),
        len(added_signatures),
        len(chain),
        int(getattr(settings, "flow_active_min_volume", 100) or 100),
        fallback_mode,
    )
    return supplemented, fallback_mode, added_signatures


def resolve_engine_empty_outputs_fallback(
    service: Any,
    *,
    outputs: list[FlowEngineOutput],
    filtered: list[dict[str, Any]],
    target_limit: int,
) -> tuple[list[FlowEngineOutput], bool]:
    if outputs or target_limit <= 0 or not filtered:
        return outputs, False
    fallback_outputs = fallback_support.build_neutral_outputs_from_chain(
        filtered=filtered,
        limit=target_limit,
    )
    if not fallback_outputs:
        return outputs, False

    service._engine_empty_output_fallback_count += 1
    service._last_engine_empty_output_fallback_at_utc = service._utc_now_iso()
    logger.warning(
        "[ActiveOptionsRuntimeService] flow pipeline produced no outputs; "
        "using neutral output fallback candidates=%d filtered_size=%d",
        len(fallback_outputs),
        len(filtered),
    )
    return fallback_outputs, True


def apply_empty_filtered_guard(
    service: Any,
    *,
    filtered: list[dict[str, Any]],
    target_limit: int,
) -> bool:
    if filtered:
        return False
    logger.warning(
        "[ActiveOptionsRuntimeService] No options above min_volume threshold — "
        "emitting neutral placeholders to keep fixed row contract."
    )
    service._empty_filter_count += 1
    service._last_empty_filter_at_utc = service._utc_now_iso()
    rows, signature = support.build_ranked_candidate([], target_limit)
    commit_or_hold_candidate(service, rows=rows, signature=signature)
    return True


def commit_or_hold_candidate(
    service: Any,
    *,
    rows: list[dict[str, Any]],
    signature: tuple[tuple[str, str, float], ...],
) -> None:
    if support.is_placeholder_signature(signature):
        service._latest_payload = rows
        service._latest_signature = signature
        clear_pending_state(service)
        return
    if service._latest_signature is None:
        service._latest_payload = rows
        service._latest_signature = signature
        clear_pending_state(service)
        return
    if support.is_placeholder_signature(service._latest_signature) and not support.is_placeholder_signature(signature):
        service._latest_payload = rows
        service._latest_signature = signature
        clear_pending_state(service)
        return
    if signature == service._latest_signature:
        service._latest_payload = rows
        clear_pending_state(service)
        return
    if signature != service._pending_signature:
        service._pending_signature = signature
        service._pending_rows = rows
        service._pending_hits = 1
        return
    service._pending_hits += 1
    if service._pending_hits < service._switch_confirm_ticks:
        return
    service._latest_payload = service._pending_rows
    service._latest_signature = service._pending_signature
    clear_pending_state(service)

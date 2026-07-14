"""ATM anchor mandatory subscription sync helpers."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.loops.shared_state import SharedLoopState

if TYPE_CHECKING:
    from app.container import AppContainer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnchorMandatorySyncResult:
    """Result of one anchor mandatory sync pass."""

    symbols: set[str]
    changed: bool
    refreshed: bool
    repaired_count: int


def _anchor_symbols(ctr: "AppContainer") -> set[str]:
    raw_symbols = ctr.atm_decay_tracker.get_anchor_symbols()
    if not isinstance(raw_symbols, set):
        raw_symbols = set(raw_symbols or [])
    return {str(symbol) for symbol in raw_symbols if str(symbol).strip()}


def _valid_refresh_spot(spot: Any) -> float | None:
    try:
        value = float(spot)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value <= 0.0:
        return None
    return value


async def sync_anchor_mandatory_symbols(
    ctr: "AppContainer",
    state: SharedLoopState,
    *,
    spot: Any,
    refresh_on_change: bool,
    reason: str,
) -> AnchorMandatorySyncResult:
    """Keep current ATM anchor legs mandatory and refresh L0 once on anchor changes."""
    symbols = _anchor_symbols(ctr)
    changed = symbols != state.last_anchor_mandatory_symbols
    ctr.option_chain_builder.set_mandatory_symbols(symbols)
    if changed:
        state.record_anchor_mandatory_sync(symbols, reason=reason)
        logger.info(
            "[AnchorMandatorySync] symbols_changed reason=%s symbols=%s",
            reason,
            sorted(symbols),
        )
    if not refresh_on_change or not changed or not symbols:
        return AnchorMandatorySyncResult(symbols, changed, False, 0)

    refresh_spot = _valid_refresh_spot(spot)
    if refresh_spot is None:
        logger.warning(
            "[AnchorMandatorySync] skipped_refresh reason=%s invalid_spot=%s symbols=%s",
            reason,
            spot,
            sorted(symbols),
        )
        return AnchorMandatorySyncResult(symbols, changed, False, 0)

    subscribed = await ctr.option_chain_builder.refresh_subscriptions_once(refresh_spot)
    repaired_count = await ctr.option_chain_builder.repair_symbols_once(
        symbols,
        log_prefix="[AnchorMandatorySync]",
    )
    logger.info(
        "[AnchorMandatorySync] refreshed reason=%s spot=%.4f mandatory=%d subscribed=%d repaired=%d",
        reason,
        refresh_spot,
        len(symbols),
        len(subscribed),
        repaired_count,
    )
    return AnchorMandatorySyncResult(symbols, changed, True, repaired_count)


async def update_atm_decay_and_sync_anchor(
    ctr: "AppContainer",
    state: SharedLoopState,
    chain: Any,
    spot: Any,
    *,
    reason: str,
) -> dict[str, Any]:
    """Update ATM decay, then protect the tracker-selected anchor legs in L0."""
    atm_decay_payload = await ctr.atm_decay_tracker.update(chain, spot)
    await sync_anchor_mandatory_symbols(
        ctr,
        state,
        spot=spot,
        refresh_on_change=True,
        reason=reason,
    )
    return atm_decay_payload

"""Housekeeping loop for background non-critical computation syncs."""

import asyncio
import logging
import time
from typing import Any

from shared.config import settings
from app.loops.shared_state import SharedLoopState

# Only for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.container import AppContainer

logger = logging.getLogger(__name__)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_active_options_row(raw: dict[str, Any]) -> dict[str, Any]:
    row = dict(raw)
    option_type = str(row.get("option_type", row.get("type", ""))).strip().upper()
    if option_type not in {"CALL", "PUT"}:
        is_call = row.get("is_call")
        option_type = "CALL" if bool(is_call) else "PUT"
    row["option_type"] = option_type

    if _to_float(row.get("implied_volatility"), 0.0) <= 0.0:
        row["implied_volatility"] = _to_float(row.get("computed_iv"), 0.0)
    if _to_float(row.get("delta"), 0.0) == 0.0:
        row["delta"] = _to_float(row.get("computed_delta"), 0.0)
    if _to_float(row.get("gamma"), 0.0) == 0.0:
        row["gamma"] = _to_float(row.get("computed_gamma"), 0.0)
    if _to_float(row.get("vanna"), 0.0) == 0.0:
        row["vanna"] = _to_float(row.get("computed_vanna"), 0.0)
    return row


def _extract_chain_rows(snapshot: Any) -> list[dict[str, Any]]:
    chain = getattr(snapshot, "chain", None)
    if chain is None:
        return []
    if hasattr(chain, "to_pylist"):
        rows = chain.to_pylist()
    elif isinstance(chain, list):
        rows = chain
    else:
        try:
            rows = list(chain)
        except TypeError:
            return []
    return [_normalize_active_options_row(row) for row in rows if isinstance(row, dict)]


async def run_housekeeping_loop(ctr: 'AppContainer', state: SharedLoopState) -> None:
    """Background loop for Active Options calculation and missing symbol sync.

    Decouples the slow Redis OI aggregation and D/E/G flow engine
    from the microsecond-sensitive agent runner loop.
    """
    update_interval = settings.websocket_update_interval
    next_tick = time.monotonic()
    last_l1_version: int | None = None
    
    while True:
        try:
            # 1. Extract context from latest computed payload (AgentB1)
            atm_iv = 0.0
            gex_regime = "NEUTRAL"
            if state.payload_dict:
                g_data = state.payload_dict.get("agent_g", {}).get("data", {})
                atm_iv = g_data.get("spy_atm_iv") or 0.0
                gex_regime = g_data.get("gex_regime", "NEUTRAL")

            # 2. Prefer latest L1 snapshot to avoid duplicate fetch-chain compute.
            l1_snapshot = state.latest_l1_snapshot
            if l1_snapshot is not None:
                l1_version = int(getattr(l1_snapshot, "version", 0) or 0)
                if l1_version > 0 and last_l1_version == l1_version:
                    logger.info(
                        "[GPU-AUDIT] housekeeping_skip_duplicate_l1 snapshot_version=%s",
                        l1_version,
                    )
                else:
                    chain = _extract_chain_rows(l1_snapshot)
                    spot = _to_float(getattr(l1_snapshot, "spot", 0.0), 0.0)
                    if atm_iv <= 0.0:
                        aggregates = getattr(l1_snapshot, "aggregates", None)
                        atm_iv = _to_float(getattr(aggregates, "atm_iv", 0.0), 0.0)
                    await ctr.active_options_service.update_background(
                        chain=chain,
                        spot=spot,
                        atm_iv=atm_iv,
                        gex_regime=gex_regime,
                        ttm_seconds=getattr(l1_snapshot, "ttm_seconds", None),
                        redis=ctr.redis_service.client,
                        limit=5,
                    )
                    last_l1_version = l1_version
            else:
                snapshot = await ctr.option_chain_builder.fetch_chain(
                    include_legacy_greeks=False,
                    caller_tag="housekeeping_fallback",
                )
                await ctr.active_options_service.update_background(
                    chain=snapshot.get("chain", []),
                    spot=snapshot.get("spot", 0.0),
                    atm_iv=atm_iv,
                    gex_regime=gex_regime,
                    ttm_seconds=snapshot.get("ttm_seconds"),
                    redis=ctr.redis_service.client,
                    limit=5,
                )

            # 3. Sync mandatory symbols (ATM anchors) back to data feed
            # This ensures the symbols used for the chart are always depth-subscribed.
            # Moved out of the compute loop into housekeeping.
            anchor_symbols = ctr.atm_decay_tracker.get_anchor_symbols()
            if anchor_symbols:
                ctr.option_chain_builder.set_mandatory_symbols(anchor_symbols)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(f"[Housekeeping] Error: {e}")
            
        next_tick += update_interval
        sleep_dur = next_tick - time.monotonic()
        if sleep_dur > 0:
            await asyncio.sleep(sleep_dur)
        else:
            next_tick = time.monotonic()
            await asyncio.sleep(0.01)

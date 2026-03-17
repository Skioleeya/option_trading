"""ActiveOptions runtime service (shared neutral service layer).

Orchestrates the three FlowEngine_D/E/G engines and the DEGComposer to
produce the final Active Options UI payload with stable VOL-first ranking.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from shared.cache.oi_snapshot import save_oi_snapshot
from shared.config import settings
from shared.models.flow_engine import FlowEngineInput, FlowEngineOutput
from shared.system.persistent_oi_store import PersistentOIStore
from . import runtime_service_support as support
from .constants import (
    ACTIVE_OPTIONS_CHARM_SURGE_END_HOUR_ET,
    ACTIVE_OPTIONS_CHARM_SURGE_START_HOUR_ET,
    ACTIVE_OPTIONS_DEFAULT_LIMIT,
    ACTIVE_OPTIONS_SWITCH_CONFIRM_TICKS,
)
from .deg_composer import DEGComposer
from .flow_engine_d import FlowEngineD
from .flow_engine_e import FlowEngineE
from .flow_engine_g import FlowEngineG

logger = logging.getLogger(__name__)


def _is_charm_surge() -> bool:
    """Return True if now is within the last 2 hours before market close (ET)."""
    now = datetime.now(ZoneInfo("US/Eastern"))
    return ACTIVE_OPTIONS_CHARM_SURGE_START_HOUR_ET <= now.hour < ACTIVE_OPTIONS_CHARM_SURGE_END_HOUR_ET


class ActiveOptionsRuntimeService:
    """Build the Active Options UI state using the DEG-FLOW composite engine."""

    def __init__(self) -> None:
        self._engine_d = FlowEngineD()
        self._engine_e = FlowEngineE()
        self._engine_g = FlowEngineG()
        self._composer = DEGComposer()
        self._oi_store = PersistentOIStore()
        self._latest_payload: list[dict[str, Any]] = []
        self._latest_signature: tuple[tuple[str, str, float], ...] | None = None
        self._pending_signature: tuple[tuple[str, str, float], ...] | None = None
        self._pending_rows: list[dict[str, Any]] = []
        self._pending_hits = 0
        self._switch_confirm_ticks = ACTIVE_OPTIONS_SWITCH_CONFIRM_TICKS

    def get_latest(self) -> list[dict[str, Any]]:
        """Return the latest cached generated rows without blocking."""
        return self._latest_payload

    async def update_background(
        self,
        chain: list[dict[str, Any]],
        spot: float,
        atm_iv: float,
        gex_regime: str = "NEUTRAL",
        ttm_seconds: float | None = None,
        redis: Any | None = None,
        limit: int = ACTIVE_OPTIONS_DEFAULT_LIMIT,
    ) -> None:
        """Run the full D+E+G pipeline and update the background cache."""
        target_limit = max(0, int(limit))
        if self._apply_zero_limit_guard(target_limit):
            return

        filtered = self._normalize_and_filter_chain(
            chain=chain,
            min_volume=settings.flow_active_min_volume,
        )
        if self._apply_empty_filtered_guard(filtered=filtered, target_limit=target_limit):
            return

        await self._save_oi_snapshot_if_enabled(redis=redis, filtered=filtered)
        outputs = await self._run_flow_pipeline(
            filtered=filtered,
            spot=spot,
            atm_iv=atm_iv,
            gex_regime=gex_regime,
            ttm_seconds=ttm_seconds,
            redis=redis,
        )

        rows, signature = self._build_ranked_candidate(outputs, target_limit)
        self._commit_or_hold_candidate(rows=rows, signature=signature)

    def _reset_cache_state(self) -> None:
        self._latest_payload = []
        self._latest_signature = None
        self._pending_signature = None
        self._pending_rows = []
        self._pending_hits = 0

    def _clear_pending_state(self) -> None:
        self._pending_signature = None
        self._pending_rows = []
        self._pending_hits = 0

    def _apply_zero_limit_guard(self, target_limit: int) -> bool:
        if target_limit > 0:
            return False
        self._reset_cache_state()
        return True

    @staticmethod
    def _normalize_and_filter_chain(
        *,
        chain: list[dict[str, Any]],
        min_volume: int,
    ) -> list[dict[str, Any]]:
        return support.normalize_and_filter_chain(chain=chain, min_volume=min_volume)

    def _apply_empty_filtered_guard(
        self,
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
        rows, signature = self._build_ranked_candidate([], target_limit)
        self._commit_or_hold_candidate(rows=rows, signature=signature)
        return True

    @staticmethod
    async def _save_oi_snapshot_if_enabled(
        *,
        redis: Any | None,
        filtered: list[dict[str, Any]],
    ) -> None:
        if redis is None:
            return
        await save_oi_snapshot(redis, filtered)

    async def _run_flow_pipeline(
        self,
        *,
        filtered: list[dict[str, Any]],
        spot: float,
        atm_iv: float,
        gex_regime: str,
        ttm_seconds: float | None,
        redis: Any | None,
    ) -> list[FlowEngineOutput]:
        inputs = [
            FlowEngineInput.from_chain_entry(opt, spot=spot, atm_iv=atm_iv)
            for opt in filtered
        ]
        inputs_by_symbol = {inp.symbol: inp for inp in inputs}

        today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
        d_results = self._engine_d.compute(inputs)
        e_results = self._engine_e.compute(inputs)
        g_results = await self._engine_g.compute(
            inputs,
            redis=redis,
            oi_store=self._oi_store,
            date_str=today_str,
        )
        return self._composer.compose(
            d_results,
            e_results,
            g_results,
            inputs_by_symbol=inputs_by_symbol,
            is_charm_surge=_is_charm_surge(),
            gex_regime=gex_regime,
            ttm_seconds=ttm_seconds,
        )

    def _commit_or_hold_candidate(
        self,
        *,
        rows: list[dict[str, Any]],
        signature: tuple[tuple[str, str, float], ...],
    ) -> None:
        # Empty-data degradation must cut over immediately (no stale retention window).
        if self._is_placeholder_signature(signature):
            self._latest_payload = rows
            self._latest_signature = signature
            self._clear_pending_state()
            return

        # First publish has no prior state; commit immediately.
        if self._latest_signature is None:
            self._latest_payload = rows
            self._latest_signature = signature
            self._clear_pending_state()
            return

        # No ranking change — refresh numeric fields in-place and clear pending candidate.
        # This keeps VOL-top composition stable while still allowing live value updates.
        if signature == self._latest_signature:
            self._latest_payload = rows
            self._clear_pending_state()
            return

        # Candidate changed — require N consecutive identical signatures before switch.
        if signature != self._pending_signature:
            self._pending_signature = signature
            self._pending_rows = rows
            self._pending_hits = 1
            return

        self._pending_hits += 1
        if self._pending_hits < self._switch_confirm_ticks:
            return

        self._latest_payload = self._pending_rows
        self._latest_signature = self._pending_signature
        self._clear_pending_state()

    # Compatibility wrappers kept to avoid broad test/caller churn during split.
    @staticmethod
    def _rank_outputs(outputs: list[FlowEngineOutput]) -> list[FlowEngineOutput]:
        return support.rank_outputs(outputs)

    @classmethod
    def _build_ranked_candidate(
        cls,
        outputs: list[FlowEngineOutput],
        limit: int,
    ) -> tuple[list[dict[str, Any]], tuple[tuple[str, str, float], ...]]:
        return support.build_ranked_candidate(outputs, limit)

    @staticmethod
    def _is_placeholder_signature(signature: tuple[tuple[str, str, float], ...]) -> bool:
        return support.is_placeholder_signature(signature)

    @staticmethod
    def _format_row(o: FlowEngineOutput, *, slot_index: int = 1) -> dict[str, Any]:
        return support.format_row(o, slot_index=slot_index)

    @staticmethod
    def _placeholder_row(slot_index: int) -> dict[str, Any]:
        return support.placeholder_row(slot_index)

    @classmethod
    def _pad_rows(cls, rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        return support.pad_rows(rows, limit)

"""ActiveOptions runtime service (shared neutral service layer).

Orchestrates the three FlowEngine_D/E/G engines and the DEGComposer to
produce the final Active Options UI payload with stable VOL-first ranking.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from shared.cache.oi_snapshot import save_oi_snapshot
from shared.config import settings
from shared.models.flow_engine import FlowEngineInput, FlowEngineOutput
from shared.system.persistent_oi_store import PersistentOIStore
from . import runtime_service_fallbacks as fallback_support
from . import runtime_service_mutations as mutations
from . import runtime_service_support as support
from .runtime_service_diagnostics import build_runtime_service_diagnostics
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

FALLBACK_MIN_CANDIDATES = 1


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
        self._empty_filter_count = 0
        self._last_empty_filter_at_utc: str | None = None
        self._empty_filter_fallback_count = 0
        self._last_empty_filter_fallback_at_utc: str | None = None
        self._partial_fallback_count = 0
        self._last_partial_fallback_at_utc: str | None = None
        self._last_partial_fallback_mode: str | None = None
        self._last_filtered_candidates_count = 0
        self._last_supplemented_rows = 0
        self._engine_empty_output_fallback_count = 0
        self._last_engine_empty_output_fallback_at_utc: str | None = None
        self._last_fallback_mode: str | None = None
        self._last_update_at_utc: str | None = None

    def get_latest(self) -> list[dict[str, Any]]:
        """Return the latest cached generated rows without blocking."""
        return self._latest_payload

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(ZoneInfo("UTC")).isoformat()

    @staticmethod
    def _fallback_enabled() -> bool:
        return bool(getattr(settings, "flow_active_empty_filter_fallback_enabled", True))

    @staticmethod
    def _fallback_max_candidates() -> int:
        return max(0, int(getattr(settings, "flow_active_empty_filter_fallback_max_candidates", 120) or 120))

    @classmethod
    def _effective_fallback_max_candidates(cls, target_limit: int) -> int:
        configured_max = cls._fallback_max_candidates()
        if configured_max > 0:
            return configured_max
        if target_limit <= 0:
            return 0
        return max(FALLBACK_MIN_CANDIDATES, target_limit)

    def get_diagnostics(self) -> dict[str, Any]:
        """Expose lightweight diagnostics for /debug/persistence_status."""
        return build_runtime_service_diagnostics(self, self._latest_payload)

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
        self._last_update_at_utc = self._utc_now_iso()
        target_limit = max(0, int(limit))
        if mutations.apply_zero_limit_guard(self, target_limit):
            return

        filtered = self._normalize_and_filter_chain(
            chain=chain,
            min_volume=settings.flow_active_min_volume,
        )
        self._last_filtered_candidates_count = len(filtered)
        filtered, empty_filter_fallback_mode = mutations.resolve_empty_filter_fallback(
            self,
            filtered=filtered,
            chain=chain,
            target_limit=target_limit,
            effective_max_candidates=self._effective_fallback_max_candidates(target_limit),
            fallback_enabled=self._fallback_enabled(),
        )
        filtered, partial_fallback_mode, partial_fallback_signatures = mutations.resolve_partial_filter_fallback(
            self,
            filtered=filtered,
            chain=chain,
            target_limit=target_limit,
        )
        if mutations.apply_empty_filtered_guard(self, filtered=filtered, target_limit=target_limit):
            self._last_fallback_mode = None
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
        outputs, used_engine_output_fallback = mutations.resolve_engine_empty_outputs_fallback(
            self,
            outputs=outputs,
            filtered=filtered,
            target_limit=target_limit,
        )

        rows, signature = self._build_ranked_candidate(outputs, target_limit)
        fallback_mode = (
            support.FALLBACK_REASON_ENGINE_EMPTY_OUTPUT
            if used_engine_output_fallback
            else partial_fallback_mode or empty_filter_fallback_mode
        )
        if used_engine_output_fallback and fallback_mode is not None:
            rows = support.mark_rows_as_synthetic_fallback(
                rows,
                fallback_reason=fallback_mode,
            )
        elif partial_fallback_mode is not None:
            rows = fallback_support.mark_rows_with_fallback_signatures(
                rows,
                fallback_reason=partial_fallback_mode,
                signatures=partial_fallback_signatures,
            )
        elif empty_filter_fallback_mode is not None:
            rows = support.mark_rows_as_synthetic_fallback(
                rows,
                fallback_reason=empty_filter_fallback_mode,
            )
        self._last_fallback_mode = fallback_mode
        mutations.commit_or_hold_candidate(self, rows=rows, signature=signature)

    def _apply_zero_limit_guard(self, target_limit: int) -> bool:
        return mutations.apply_zero_limit_guard(self, target_limit)

    @staticmethod
    def _normalize_and_filter_chain(
        *,
        chain: list[dict[str, Any]],
        min_volume: int,
    ) -> list[dict[str, Any]]:
        return support.normalize_and_filter_chain(chain=chain, min_volume=min_volume)

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
        mutations.commit_or_hold_candidate(self, rows=rows, signature=signature)

    # Compatibility wrappers kept to avoid broad test/caller churn during split.
    @staticmethod
    def _rank_outputs(outputs: list[FlowEngineOutput]) -> list[FlowEngineOutput]: return support.rank_outputs(outputs)

    @classmethod
    def _build_ranked_candidate(
        cls,
        outputs: list[FlowEngineOutput],
        limit: int,
    ) -> tuple[list[dict[str, Any]], tuple[tuple[str, str, float], ...]]: return support.build_ranked_candidate(outputs, limit)

    @staticmethod
    def _is_placeholder_signature(signature: tuple[tuple[str, str, float], ...]) -> bool: return support.is_placeholder_signature(signature)

    @staticmethod
    def _format_row(o: FlowEngineOutput, *, slot_index: int = 1) -> dict[str, Any]: return support.format_row(o, slot_index=slot_index)

    @staticmethod
    def _placeholder_row(slot_index: int) -> dict[str, Any]: return support.placeholder_row(slot_index)

    @classmethod
    def _pad_rows(cls, rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]: return support.pad_rows(rows, limit)

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
    ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_GAMMA,
    ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_TURNOVER,
    ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED,
    ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_LIVE,
    ACTIVE_OPTIONS_SWITCH_CONFIRM_TICKS,
)
from .deg_composer import DEGComposer
from .flow_engine_d import FlowEngineD
from .flow_engine_e import FlowEngineE
from .flow_engine_g import FlowEngineG

logger = logging.getLogger(__name__)
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
        latest = self._latest_payload
        placeholder_rows = sum(1 for row in latest if bool(row.get("is_placeholder", False)))
        synthetic_rows = sum(
            1
            for row in latest
            if bool(row.get("row_quality") == support.ROW_QUALITY_FALLBACK_SYNTHETIC)
            or bool(row.get("is_synthetic_fallback", False))
        )
        total_rows = len(latest)
        real_rows = max(0, total_rows - placeholder_rows)
        real_non_synthetic = max(0, real_rows - synthetic_rows)
        degraded_rows = sum(
            1
            for row in latest
            if str(row.get("flow_signal_state", "")).strip().upper()
            == ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_DEGRADED
        )
        live_rows = sum(
            1
            for row in latest
            if str(row.get("flow_signal_state", "")).strip().upper()
            == ACTIVE_OPTIONS_FLOW_SIGNAL_STATE_LIVE
        )
        missing_gamma_rows = sum(
            1
            for row in latest
            if str(row.get("flow_signal_reason", "")).strip()
            == ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_GAMMA
        )
        missing_turnover_rows = sum(
            1
            for row in latest
            if str(row.get("flow_signal_reason", "")).strip()
            == ACTIVE_OPTIONS_FLOW_SIGNAL_REASON_MISSING_TURNOVER
        )
        fallback_enabled = self._fallback_enabled()
        configured_max_candidates = self._fallback_max_candidates()
        return {
            "rows_total": total_rows,
            "rows_placeholder": placeholder_rows,
            "rows_real": real_rows,
            "rows_real_non_synthetic": real_non_synthetic,
            "rows_synthetic_fallback": synthetic_rows,
            "degraded_rows": degraded_rows,
            "live_rows": live_rows,
            "missing_gamma_rows": missing_gamma_rows,
            "missing_turnover_rows": missing_turnover_rows,
            "all_placeholder": bool(total_rows > 0 and placeholder_rows == total_rows),
            "empty_filter_count": self._empty_filter_count,
            "last_empty_filter_at_utc": self._last_empty_filter_at_utc,
            "empty_filter_fallback_count": self._empty_filter_fallback_count,
            "last_empty_filter_fallback_at_utc": self._last_empty_filter_fallback_at_utc,
            "engine_empty_output_fallback_count": self._engine_empty_output_fallback_count,
            "last_engine_empty_output_fallback_at_utc": self._last_engine_empty_output_fallback_at_utc,
            "last_fallback_mode": self._last_fallback_mode,
            "last_update_at_utc": self._last_update_at_utc,
            "min_volume_threshold": int(getattr(settings, "flow_active_min_volume", 100) or 100),
            "empty_filter_fallback_enabled": fallback_enabled,
            "empty_filter_fallback_max_candidates": configured_max_candidates,
        }

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
        if self._apply_zero_limit_guard(target_limit):
            return

        filtered = self._normalize_and_filter_chain(
            chain=chain,
            min_volume=settings.flow_active_min_volume,
        )
        filtered, empty_filter_fallback_mode = self._resolve_empty_filter_fallback(
            filtered=filtered,
            chain=chain,
            target_limit=target_limit,
        )
        if self._apply_empty_filtered_guard(filtered=filtered, target_limit=target_limit):
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
        outputs, used_engine_output_fallback = self._resolve_engine_empty_outputs_fallback(
            outputs=outputs,
            filtered=filtered,
            target_limit=target_limit,
        )

        rows, signature = self._build_ranked_candidate(outputs, target_limit)
        fallback_mode = support.FALLBACK_REASON_ENGINE_EMPTY_OUTPUT if used_engine_output_fallback else empty_filter_fallback_mode
        if fallback_mode is not None:
            rows = support.mark_rows_as_synthetic_fallback(
                rows,
                fallback_reason=fallback_mode,
            )
        self._last_fallback_mode = fallback_mode
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

    @staticmethod
    def _build_empty_filter_fallback(
        chain: list[dict[str, Any]],
        *,
        max_candidates: int,
    ) -> tuple[list[dict[str, Any]], str]:
        return support.fallback_candidates_when_empty(
            chain=chain,
            max_candidates=max(0, int(max_candidates)),
        )

    def _resolve_empty_filter_fallback(
        self,
        *,
        filtered: list[dict[str, Any]],
        chain: list[dict[str, Any]],
        target_limit: int,
    ) -> tuple[list[dict[str, Any]], str | None]:
        if filtered:
            return filtered, None

        if target_limit <= 0:
            return filtered, None

        fallback_enabled = self._fallback_enabled()
        effective_max_candidates = self._effective_fallback_max_candidates(target_limit)
        if effective_max_candidates <= 0:
            return filtered, None

        if not fallback_enabled and chain:
            logger.warning(
                "[ActiveOptionsRuntimeService] empty-filter fallback disabled by config but chain is non-empty; "
                "forcing hard fallback for continuity chain_size=%d",
                len(chain),
            )

        fallback_candidates, fallback_mode = self._build_empty_filter_fallback(
            chain,
            max_candidates=effective_max_candidates,
        )
        if not fallback_candidates:
            return filtered, None

        self._empty_filter_fallback_count += 1
        self._last_empty_filter_fallback_at_utc = self._utc_now_iso()
        if fallback_mode == "hard_chain":
            logger.warning(
                "[ActiveOptionsRuntimeService] No options above min_volume threshold — "
                "using hard fallback from non-empty chain candidates=%d chain_size=%d threshold=%d",
                len(fallback_candidates),
                len(chain),
                int(getattr(settings, "flow_active_min_volume", 100) or 100),
            )
        else:
            logger.warning(
                "[ActiveOptionsRuntimeService] No options above min_volume threshold — "
                "using turnover/open_interest fallback candidates=%d threshold=%d",
                len(fallback_candidates),
                int(getattr(settings, "flow_active_min_volume", 100) or 100),
            )
        resolved_mode = str(fallback_mode).strip() if fallback_mode is not None else None
        return fallback_candidates, resolved_mode

    def _resolve_engine_empty_outputs_fallback(
        self,
        *,
        outputs: list[FlowEngineOutput],
        filtered: list[dict[str, Any]],
        target_limit: int,
    ) -> tuple[list[FlowEngineOutput], bool]:
        if outputs:
            return outputs, False
        if target_limit <= 0:
            return outputs, False
        if not filtered:
            return outputs, False

        fallback_outputs = support.build_neutral_outputs_from_chain(
            filtered=filtered,
            limit=target_limit,
        )
        if not fallback_outputs:
            return outputs, False

        self._engine_empty_output_fallback_count += 1
        self._last_engine_empty_output_fallback_at_utc = self._utc_now_iso()
        logger.warning(
            "[ActiveOptionsRuntimeService] flow pipeline produced no outputs; "
            "using neutral output fallback candidates=%d filtered_size=%d",
            len(fallback_outputs),
            len(filtered),
        )
        return fallback_outputs, True

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
        self._empty_filter_count += 1
        self._last_empty_filter_at_utc = self._utc_now_iso()
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

        # Recovery path: once we have any non-placeholder candidate, do not keep
        # neutral placeholders behind a 3-tick confirmation window.
        if (
            self._is_placeholder_signature(self._latest_signature)
            and not self._is_placeholder_signature(signature)
        ):
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

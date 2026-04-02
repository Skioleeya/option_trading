"""Neutral Active Options runtime surface with Rust-backed owners."""

from __future__ import annotations

import inspect
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from shared.cache.oi_snapshot import PersistentOIStore, save_oi_snapshot
from shared.config import settings
from shared_rust.models import FlowEngineInput, FlowEngineOutput
from shared_rust.services import (
    DEGComposer,
    FlowEngineD,
    FlowEngineE,
    FlowEngineG,
    active_options_build_neutral_outputs_from_chain,
    active_options_build_ranked_candidate,
    active_options_build_runtime_diagnostics,
    active_options_fallback_candidates_when_empty,
    active_options_format_row,
    active_options_is_placeholder_signature,
    active_options_mark_rows_as_synthetic_fallback,
    active_options_mark_rows_with_fallback_signatures,
    active_options_normalize_and_filter_chain,
    active_options_pad_rows,
    active_options_rank_outputs,
    active_options_supplement_partial_candidates,
)

from .active_options_constants import (
    ACTIVE_OPTIONS_CHARM_SURGE_END_HOUR_ET,
    ACTIVE_OPTIONS_CHARM_SURGE_START_HOUR_ET,
    ACTIVE_OPTIONS_DEFAULT_LIMIT,
    ACTIVE_OPTIONS_SWITCH_CONFIRM_TICKS,
)

logger = logging.getLogger(__name__)

FALLBACK_MIN_CANDIDATES = 1
FALLBACK_REASON_ENGINE_EMPTY_OUTPUT = "engine_empty_output"
FALLBACK_REASON_SUBTHRESHOLD_VOLUME = "subthreshold_volume"


def _is_charm_surge() -> bool:
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
        return active_options_build_runtime_diagnostics(
            latest_rows=self._latest_payload,
            empty_filter_count=self._empty_filter_count,
            last_empty_filter_at_utc=self._last_empty_filter_at_utc,
            empty_filter_fallback_count=self._empty_filter_fallback_count,
            last_empty_filter_fallback_at_utc=self._last_empty_filter_fallback_at_utc,
            partial_fallback_count=self._partial_fallback_count,
            last_partial_fallback_at_utc=self._last_partial_fallback_at_utc,
            last_partial_fallback_mode=self._last_partial_fallback_mode,
            filtered_candidates_count=self._last_filtered_candidates_count,
            supplemented_rows=self._last_supplemented_rows,
            engine_empty_output_fallback_count=self._engine_empty_output_fallback_count,
            last_engine_empty_output_fallback_at_utc=self._last_engine_empty_output_fallback_at_utc,
            last_fallback_mode=self._last_fallback_mode,
            last_update_at_utc=self._last_update_at_utc,
            min_volume_threshold=int(getattr(settings, "flow_active_min_volume", 100) or 100),
            empty_filter_fallback_enabled=self._fallback_enabled(),
            empty_filter_fallback_max_candidates=self._fallback_max_candidates(),
        )

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
        self._last_update_at_utc = self._utc_now_iso()
        target_limit = max(0, int(limit))
        if self._apply_zero_limit_guard(target_limit):
            return

        filtered = self._normalize_and_filter_chain(chain=chain, min_volume=settings.flow_active_min_volume)
        self._last_filtered_candidates_count = len(filtered)

        empty_filter_fallback_mode: str | None = None
        if not filtered and target_limit > 0:
            if not self._fallback_enabled() and chain:
                logger.warning(
                    "[ActiveOptionsRuntimeService] empty-filter fallback disabled by config but chain is non-empty; "
                    "forcing continuity fallback chain_size=%d",
                    len(chain),
                )
            fallback_candidates, fallback_mode = active_options_fallback_candidates_when_empty(
                chain=chain,
                max_candidates=self._effective_fallback_max_candidates(target_limit),
            )
            if fallback_candidates:
                filtered = list(fallback_candidates)
                empty_filter_fallback_mode = str(fallback_mode or "").strip() or None
                self._empty_filter_fallback_count += 1
                self._last_empty_filter_fallback_at_utc = self._utc_now_iso()

        partial_fallback_mode: str | None = None
        partial_fallback_signatures: set[tuple[str, str, float]] = set()
        self._last_supplemented_rows = 0
        self._last_partial_fallback_mode = None
        if 0 < len(filtered) < target_limit:
            supplemented, partial_mode, added = active_options_supplement_partial_candidates(
                filtered=filtered,
                chain=chain,
                target_limit=target_limit,
            )
            if added:
                filtered = list(supplemented)
                partial_fallback_mode = partial_mode
                partial_fallback_signatures = set(added)
                self._partial_fallback_count += 1
                self._last_partial_fallback_at_utc = self._utc_now_iso()
                self._last_partial_fallback_mode = partial_mode
                self._last_supplemented_rows = len(added)

        if not filtered:
            logger.warning(
                "[ActiveOptionsRuntimeService] No options above min_volume threshold - "
                "emitting neutral placeholders to keep fixed row contract."
            )
            self._empty_filter_count += 1
            self._last_empty_filter_at_utc = self._utc_now_iso()
            rows, signature = self._build_ranked_candidate([], target_limit)
            self._commit_or_hold_candidate(rows=rows, signature=signature)
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

        used_engine_output_fallback = False
        if not outputs and filtered and target_limit > 0:
            fallback_outputs = active_options_build_neutral_outputs_from_chain(
                filtered=filtered,
                limit=target_limit,
            )
            if fallback_outputs:
                outputs = list(fallback_outputs)
                used_engine_output_fallback = True
                self._engine_empty_output_fallback_count += 1
                self._last_engine_empty_output_fallback_at_utc = self._utc_now_iso()

        rows, signature = self._build_ranked_candidate(outputs, target_limit)
        fallback_mode = (
            FALLBACK_REASON_ENGINE_EMPTY_OUTPUT
            if used_engine_output_fallback
            else partial_fallback_mode or empty_filter_fallback_mode
        )
        if used_engine_output_fallback and fallback_mode is not None:
            rows = active_options_mark_rows_as_synthetic_fallback(rows, fallback_reason=fallback_mode)
        elif partial_fallback_mode is not None:
            rows = active_options_mark_rows_with_fallback_signatures(
                rows,
                fallback_reason=partial_fallback_mode,
                signatures=list(partial_fallback_signatures),
            )
        elif empty_filter_fallback_mode == FALLBACK_REASON_SUBTHRESHOLD_VOLUME:
            signatures = [
                (
                    str(row.get("contract_symbol", "")),
                    str(row.get("option_type", "CALL")).upper(),
                    round(float(row.get("strike", 0.0) or 0.0), 4),
                )
                for row in rows
                if not bool(row.get("is_placeholder", False))
            ]
            rows = active_options_mark_rows_with_fallback_signatures(
                rows,
                fallback_reason=empty_filter_fallback_mode,
                signatures=signatures,
            )
        elif empty_filter_fallback_mode is not None:
            rows = active_options_mark_rows_as_synthetic_fallback(
                rows,
                fallback_reason=empty_filter_fallback_mode,
            )

        self._last_fallback_mode = fallback_mode
        self._commit_or_hold_candidate(rows=rows, signature=signature)

    def _apply_zero_limit_guard(self, target_limit: int) -> bool:
        if target_limit > 0:
            return False
        self._latest_payload = []
        self._latest_signature = None
        self._pending_signature = None
        self._pending_rows = []
        self._pending_hits = 0
        return True

    @staticmethod
    def _normalize_and_filter_chain(
        *,
        chain: list[dict[str, Any]],
        min_volume: int,
    ) -> list[dict[str, Any]]:
        return list(active_options_normalize_and_filter_chain(chain=chain, min_volume=min_volume))

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
            FlowEngineInput.from_chain_entry(option_row, spot=spot, atm_iv=atm_iv)
            for option_row in filtered
        ]
        inputs_by_symbol = {input_row.symbol: input_row for input_row in inputs}
        today_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
        d_results = self._engine_d.compute(inputs)
        e_results = self._engine_e.compute(inputs)
        g_results = self._engine_g.compute(
            inputs,
            redis=redis,
            oi_store=self._oi_store,
            date_str=today_str,
        )
        if inspect.isawaitable(g_results):
            g_results = await g_results
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
        if self._is_placeholder_signature(signature):
            self._latest_payload = rows
            self._latest_signature = signature
            self._pending_signature = None
            self._pending_rows = []
            self._pending_hits = 0
            return
        if self._latest_signature is None:
            self._latest_payload = rows
            self._latest_signature = signature
            self._pending_signature = None
            self._pending_rows = []
            self._pending_hits = 0
            return
        if self._is_placeholder_signature(self._latest_signature) and not self._is_placeholder_signature(signature):
            self._latest_payload = rows
            self._latest_signature = signature
            self._pending_signature = None
            self._pending_rows = []
            self._pending_hits = 0
            return
        if signature == self._latest_signature:
            self._latest_payload = rows
            self._pending_signature = None
            self._pending_rows = []
            self._pending_hits = 0
            return
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
        self._pending_signature = None
        self._pending_rows = []
        self._pending_hits = 0

    @staticmethod
    def _rank_outputs(outputs: list[FlowEngineOutput]) -> list[FlowEngineOutput]:
        return list(active_options_rank_outputs(outputs))

    @classmethod
    def _build_ranked_candidate(
        cls,
        outputs: list[FlowEngineOutput],
        limit: int,
    ) -> tuple[list[dict[str, Any]], tuple[tuple[str, str, float], ...]]:
        rows, signature = active_options_build_ranked_candidate(outputs, limit)
        return list(rows), tuple(signature)

    @staticmethod
    def _is_placeholder_signature(signature: tuple[tuple[str, str, float], ...]) -> bool:
        return bool(active_options_is_placeholder_signature(list(signature)))

    @staticmethod
    def _format_row(output: FlowEngineOutput, *, slot_index: int = 1) -> dict[str, Any]:
        return dict(active_options_format_row(output, slot_index))

    @staticmethod
    def _placeholder_row(slot_index: int) -> dict[str, Any]:
        return dict(active_options_pad_rows([], slot_index)[slot_index - 1])

    @classmethod
    def _pad_rows(cls, rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        return list(active_options_pad_rows(rows, limit))


__all__ = ["ActiveOptionsRuntimeService"]

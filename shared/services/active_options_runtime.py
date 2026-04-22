"""Neutral Active Options runtime surface with Rust-backed owners. (strict)"""

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
    active_options_format_row,
    active_options_normalize_and_filter_chain,
    active_options_rank_outputs,
)
from .active_options_runtime_metrics import summarize_chain_input

from .active_options_constants import (
    ACTIVE_OPTIONS_CHARM_SURGE_END_HOUR_ET,
    ACTIVE_OPTIONS_CHARM_SURGE_START_HOUR_ET,
    ACTIVE_OPTIONS_DEFAULT_LIMIT,
)

logger = logging.getLogger(__name__)


class ActiveOptionsHardFailure(RuntimeError):
    """Hard-stop exception for strict no-fallback ActiveOptions runtime failures."""


def _is_charm_surge() -> bool:
    now = datetime.now(ZoneInfo("US/Eastern"))
    return ACTIVE_OPTIONS_CHARM_SURGE_START_HOUR_ET <= now.hour < ACTIVE_OPTIONS_CHARM_SURGE_END_HOUR_ET


class ActiveOptionsRuntimeService:
    """Build Active Options state with strict no-fallback semantics."""

    def __init__(self) -> None:
        self._engine_d = FlowEngineD()
        self._engine_e = FlowEngineE()
        self._engine_g = FlowEngineG()
        self._composer = DEGComposer()
        self._oi_store = PersistentOIStore()
        self._latest_payload: list[dict[str, Any]] = []
        self._latest_signature: tuple[tuple[str, str, float], ...] | None = None
        self._empty_filter_count = 0
        self._last_empty_filter_at_utc: str | None = None
        self._last_filtered_candidates_count = 0
        self._last_update_at_utc: str | None = None
        self._last_input_chain_size = 0
        self._last_input_day_volume_gt_zero = 0
        self._last_input_current_volume_gt_zero = 0
        self._last_input_turnover_gt_zero = 0
        self._last_input_gamma_nonzero = 0
        self._spot_window_steps = max(0, int(settings.flow_active_spot_window_steps))
        self._latest_source_version = 0
        self._halted = False
        self._halt_reason: str | None = None
        self._halted_at_utc: str | None = None

    def get_latest(self) -> list[dict[str, Any]]:
        return self._latest_payload

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(ZoneInfo("UTC")).isoformat()

    def get_diagnostics(self) -> dict[str, Any]:
        rows = self._latest_payload
        rows_total = len(rows)
        rows_placeholder = sum(1 for row in rows if bool(row.get("is_placeholder", False)))
        rows_real = max(0, rows_total - rows_placeholder)
        degraded_rows = sum(
            1
            for row in rows
            if str(row.get("flow_signal_state", "LIVE") or "LIVE").upper() != "LIVE"
        )
        live_rows = max(0, rows_total - degraded_rows)
        missing_turnover_rows = sum(
            1
            for row in rows
            if not bool(row.get("is_placeholder", False))
            and float(row.get("turnover", 0.0) or 0.0) <= 0.0
        )
        return {
            "rows_total": rows_total,
            "rows_placeholder": rows_placeholder,
            "rows_real": rows_real,
            "rows_real_non_synthetic": rows_real,
            "degraded_rows": degraded_rows,
            "live_rows": live_rows,
            "missing_gamma_rows": 0,
            "missing_turnover_rows": missing_turnover_rows,
            "all_placeholder": rows_total > 0 and rows_placeholder == rows_total,
            "empty_filter_count": self._empty_filter_count,
            "last_empty_filter_at_utc": self._last_empty_filter_at_utc,
            "filtered_candidates_count": self._last_filtered_candidates_count,
            "input_chain_size_last": self._last_input_chain_size,
            "input_day_volume_gt_zero_last": self._last_input_day_volume_gt_zero,
            "input_current_volume_gt_zero_last": self._last_input_current_volume_gt_zero,
            "input_turnover_gt_zero_last": self._last_input_turnover_gt_zero,
            "input_gamma_nonzero_last": self._last_input_gamma_nonzero,
            "spot_window_steps": self._spot_window_steps,
            "latest_source_version": self._latest_source_version,
            "strict_no_fallback": True,
            "halted": self._halted,
            "halt_reason": self._halt_reason,
            "halted_at_utc": self._halted_at_utc,
            "last_update_at_utc": self._last_update_at_utc,
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
        source_version: int | None = None,
    ) -> None:
        if self._halted:
            raise ActiveOptionsHardFailure(
                f"service_halted: reason={self._halt_reason or 'unknown'} halted_at_utc={self._halted_at_utc or 'unknown'}"
            )

        self._last_update_at_utc = self._utc_now_iso()
        target_limit = max(0, int(limit))
        self._spot_window_steps = max(0, int(settings.flow_active_spot_window_steps))
        if source_version is not None:
            source_version_int = max(0, int(source_version))
            if source_version_int > 0:
                self._latest_source_version = source_version_int

        input_stats = summarize_chain_input(chain=chain)
        self._last_input_chain_size = int(input_stats["chain_size"])
        self._last_input_day_volume_gt_zero = int(input_stats["day_volume_gt_zero"])
        self._last_input_current_volume_gt_zero = int(input_stats["current_volume_gt_zero"])
        self._last_input_turnover_gt_zero = int(input_stats["turnover_gt_zero"])
        self._last_input_gamma_nonzero = int(input_stats["gamma_nonzero"])
        logger.debug(
            "[ActiveOptionsFlow] runtime_input chain_size=%s spot_window_steps=%s "
            "day_volume_gt_zero=%s current_volume_gt_zero=%s "
            "turnover_gt_zero=%s gamma_nonzero=%s",
            self._last_input_chain_size,
            self._spot_window_steps,
            self._last_input_day_volume_gt_zero,
            self._last_input_current_volume_gt_zero,
            self._last_input_turnover_gt_zero,
            self._last_input_gamma_nonzero,
        )
        if self._apply_zero_limit_guard(target_limit):
            return

        filtered = self._normalize_and_filter_chain(
            chain=chain,
            spot=spot,
            spot_window_steps=self._spot_window_steps,
        )
        self._last_filtered_candidates_count = len(filtered)
        logger.debug(
            "[ActiveOptionsFlow] filtered_candidates count=%s target_limit=%s halted=%s",
            self._last_filtered_candidates_count,
            target_limit,
            self._halted,
        )

        if not filtered and target_limit > 0:
            self._empty_filter_count += 1
            self._last_empty_filter_at_utc = self._utc_now_iso()
            self._halt_and_raise(
                reason="normalized_chain_empty_no_candidates",
                chain_size=len(chain),
                target_limit=target_limit,
                turnover_gt_zero=self._last_input_turnover_gt_zero,
                gamma_nonzero=self._last_input_gamma_nonzero,
            )

        await self._save_oi_snapshot_if_enabled(redis=redis, filtered=filtered)
        outputs = await self._run_flow_pipeline(
            filtered=filtered,
            spot=spot,
            atm_iv=atm_iv,
            gex_regime=gex_regime,
            ttm_seconds=ttm_seconds,
            redis=redis,
        )

        if not outputs and target_limit > 0:
            self._halt_and_raise(
                reason="engine_empty_output",
                filtered_count=len(filtered),
                target_limit=target_limit,
            )

        rows, signature = self._build_ranked_candidate(outputs, target_limit)
        if not rows and target_limit > 0:
            self._halt_and_raise(
                reason="no_rows_after_ranking",
                outputs_count=len(outputs),
                target_limit=target_limit,
            )
        self._latest_payload = self._sanitize_output_rows(rows)
        self._latest_signature = signature

    def _apply_zero_limit_guard(self, target_limit: int) -> bool:
        if target_limit > 0:
            return False
        self._latest_payload = []
        self._latest_signature = None
        self._latest_source_version = 0
        return True

    def _halt_and_raise(self, reason: str, **context: Any) -> None:
        self._halted = True
        self._halt_reason = reason
        self._halted_at_utc = self._utc_now_iso()
        logger.error(
            "[ActiveOptionsRuntimeService] HARD_FAIL reason=%s halted_at_utc=%s context=%s",
            reason,
            self._halted_at_utc,
            context,
        )
        raise ActiveOptionsHardFailure(f"{reason}: {context}")

    @staticmethod
    def _normalize_and_filter_chain(
        *,
        chain: list[dict[str, Any]],
        spot: float,
        spot_window_steps: int,
    ) -> list[dict[str, Any]]:
        return list(
            active_options_normalize_and_filter_chain(
                chain=chain,
                spot=spot,
                spot_window_steps=spot_window_steps,
            )
        )

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

    @staticmethod
    def _sanitize_output_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sanitized: list[dict[str, Any]] = []
        for idx, raw in enumerate(rows, start=1):
            row = dict(raw)
            row.pop("fallback_reason", None)
            row.pop("is_synthetic_fallback", None)
            row["is_placeholder"] = False
            row["slot_index"] = idx
            row["row_quality"] = "REAL"
            row["flow_signal_state"] = "LIVE"
            row["flow_signal_reason"] = None
            sanitized.append(row)
        return sanitized

    @staticmethod
    def _rank_outputs(outputs: list[FlowEngineOutput]) -> list[FlowEngineOutput]:
        return list(active_options_rank_outputs(outputs))

    @classmethod
    def _build_ranked_candidate(
        cls,
        outputs: list[FlowEngineOutput],
        limit: int,
    ) -> tuple[list[dict[str, Any]], tuple[tuple[str, str, float], ...]]:
        if limit <= 0:
            return [], ()
        ranked = cls._rank_outputs(outputs)
        limited = ranked[:limit]
        rows = [dict(active_options_format_row(item, idx + 1)) for idx, item in enumerate(limited)]
        signature = tuple(
            (
                str(row.get("symbol", row.get("contract_symbol", ""))),
                str(row.get("option_type", "CALL")).upper(),
                round(float(row.get("strike", 0.0) or 0.0), 4),
            )
            for row in rows
        )
        return rows, signature


__all__ = ["ActiveOptionsRuntimeService", "ActiveOptionsHardFailure"]

"""Copy-on-write payload assembler for L3."""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone
from typing import Any

from l3_assembly.assembly.payload_assembler_support import (
    SnapshotData,
    convert_active_option,
    extract_wall_dyn_payload,
    normalize_volume_map,
    to_utc_iso,
)
from l3_assembly.events.payload_events import (
    FrozenPayload,
    MicroStatsState,
    MTFFlowState,
    SignalData,
    TacticalTriadState,
    UIState,
)
from l3_assembly.presenters.depth_profile import DepthProfilePresenterV2
from l3_assembly.presenters.micro_stats import MicroStatsPresenterV2
from l3_assembly.presenters.mtf_flow import MTFFlowPresenterV2
from l3_assembly.presenters.skew_dynamics import SkewDynamicsPresenterV2
from l3_assembly.presenters.tactical_triad import TacticalTriadPresenterV2
from l3_assembly.presenters.wall_migration import WallMigrationPresenterV2

logger = logging.getLogger(__name__)


class PayloadAssemblerV2:
    """Assemble immutable payloads from L1/L2 contracts."""

    def assemble(
        self,
        decision: Any,
        snapshot: Any,
        atm_decay: dict[str, Any] | None,
        active_options: Any = None,
        ui_metrics: dict[str, Any] | None = None,
    ) -> FrozenPayload:
        start = time.monotonic()
        try:
            signal = SignalData.from_decision_output(decision)
        except Exception as exc:
            logger.warning("[L3 Assembler] SignalData extraction failed: %s", exc)
            signal = SignalData.neutral()

        try:
            snap_data = self._extract_snapshot_data(snapshot, decision, ui_metrics)
        except Exception as exc:
            logger.warning("[L3 Assembler] Snapshot extraction failed: %s", exc)
            snap_data = SnapshotData()

        drift_ms, drift_warning = self._compute_drift(
            snap_data.source_data_timestamp_utc,
            signal,
        )
        ui_flip_level = self._resolve_ui_flip_level(snap_data)
        ui_state = self._build_ui_state(
            snap_data,
            active_options or (),
            flip_level=ui_flip_level,
        )
        fused_signal, micro_structure = self._extract_l2_payload(decision, ui_metrics)
        now_iso = datetime.now(timezone.utc).isoformat()

        payload = FrozenPayload(
            data_timestamp=self._resolve_data_timestamp(
                snap_data.source_data_timestamp_utc,
                signal,
                now_iso,
            ),
            broadcast_timestamp=now_iso,
            spot=snap_data.spot,
            version=signal.version,
            drift_ms=drift_ms,
            drift_warning=drift_warning,
            signal=signal,
            ui_state=ui_state,
            atm=atm_decay,
            atm_iv=snap_data.atm_iv,
            net_gex=snap_data.net_gex,
            gamma_walls={"call_wall": snap_data.call_wall, "put_wall": snap_data.put_wall},
            gamma_flip_level=ui_flip_level,
            fused_signal=fused_signal,
            micro_structure=micro_structure,
            header_volatility=snap_data.header_volatility,
            rust_active=snap_data.rust_active,
            shm_stats=snap_data.shm_stats,
            governor_telemetry=snap_data.governor_telemetry,
        )
        logger.debug(
            "[L3 Assembler] assembled in %.2fms, spot=%s, version=%s",
            (time.monotonic() - start) * 1000.0,
            snap_data.spot,
            signal.version,
        )
        return payload

    def _extract_snapshot_data(
        self,
        snapshot: Any,
        decision: Any,
        ui_metrics: dict[str, Any] | None,
    ) -> SnapshotData:
        data = SnapshotData()

        if hasattr(snapshot, "spot") and hasattr(snapshot, "aggregates"):
            aggregates = getattr(snapshot, "aggregates", None)
            data.spot = float(snapshot.spot or 0.0)
            data.atm_iv = float(getattr(aggregates, "atm_iv", 0.0) or 0.0)
            data.flip_level = float(getattr(aggregates, "flip_level", 0.0) or 0.0)
            data.flip_level_cumulative = float(
                getattr(aggregates, "flip_level_cumulative", data.flip_level) or 0.0
            )
            data.zero_gamma_level = float(getattr(aggregates, "zero_gamma_level", 0.0) or 0.0)
            data.snapshot_time = getattr(snapshot, "computed_at", None)
            data.per_strike_gex = getattr(aggregates, "per_strike_gex", [])
            data.net_gex = float(getattr(aggregates, "net_gex", 0.0) or 0.0)
            data.call_wall = float(getattr(aggregates, "call_wall", 0.0) or 0.0)
            data.put_wall = float(getattr(aggregates, "put_wall", 0.0) or 0.0)

            metadata = getattr(snapshot, "extra_metadata", {}) or {}
            data.rust_active = bool(metadata.get("rust_active", False))
            data.shm_stats = metadata.get("shm_stats")
            data.governor_telemetry = dict(metadata.get("governor_telemetry") or {})
            data.volume_map = normalize_volume_map(
                metadata.get("volume_map", getattr(snapshot, "volume_map", {}))
            )
            data.source_data_timestamp_utc = metadata.get("source_data_timestamp_utc")
        elif isinstance(snapshot, dict):
            data.spot = float(snapshot.get("spot", 0.0) or 0.0)
            data.atm_iv = float(snapshot.get("atm_iv", snapshot.get("spy_atm_iv", 0.0)) or 0.0)
            data.snapshot_time = snapshot.get("as_of")
            data.source_data_timestamp_utc = snapshot.get("as_of_utc") or snapshot.get("as_of")
            data.volume_map = normalize_volume_map(snapshot.get("volume_map"))
            data.net_gex = float(snapshot.get("net_gex", 0.0) or 0.0)
            data.call_wall = float(snapshot.get("call_wall", 0.0) or 0.0)
            data.put_wall = float(snapshot.get("put_wall", 0.0) or 0.0)
            data.flip_level = float(snapshot.get("flip_level", 0.0) or 0.0)
            data.flip_level_cumulative = float(
                snapshot.get("flip_level_cumulative", data.flip_level) or 0.0
            )
            data.zero_gamma_level = float(snapshot.get("zero_gamma_level", 0.0) or 0.0)
            data.rust_active = bool(snapshot.get("rust_active", False))
            data.shm_stats = snapshot.get("shm_stats")
            data.governor_telemetry = dict(snapshot.get("governor_telemetry") or {})

        if decision is not None:
            try:
                data.gex_regime = decision.signal_summary.get("gex_regime", "NEUTRAL")
                data.vanna_state = decision.signal_summary.get("vanna_state", "NORMAL")
            except AttributeError:
                pass

        if ui_metrics:
            data.gex_regime = ui_metrics.get("gex_regime", data.gex_regime)
            data.vanna_state = ui_metrics.get("vanna_state", data.vanna_state)
            data.momentum = ui_metrics.get("momentum", data.momentum)
            data.vrp = ui_metrics.get("vrp", data.vrp)
            data.vrp_state = ui_metrics.get("vrp_state", data.vrp_state)
            data.net_charm = ui_metrics.get("net_charm", data.net_charm)
            data.svol_corr = ui_metrics.get("svol_corr", data.svol_corr)
            data.svol_state = ui_metrics.get("svol_state", data.svol_state)
            data.wall_migration_data = ui_metrics.get(
                "wall_migration_data",
                data.wall_migration_data,
            )
            data.wall_dyn = extract_wall_dyn_payload(data.wall_migration_data)
            data.mtf_consensus = ui_metrics.get("mtf_consensus", data.mtf_consensus)
            data.skew_dynamics = ui_metrics.get("skew_dynamics", data.skew_dynamics)
            data.iv_velocity = ui_metrics.get("iv_velocity", data.iv_velocity)
            data.header_volatility = ui_metrics.get(
                "header_volatility",
                data.header_volatility,
            )

        return data

    @staticmethod
    def _extract_l2_payload(
        decision: Any,
        ui_metrics: dict[str, Any] | None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        fused_signal: dict[str, Any] | None = None
        micro_structure: dict[str, Any] | None = None
        try:
            if decision is not None:
                raw_data = getattr(decision, "data", None) or {}
                fused_signal = raw_data.get("fused_signal")
                micro_structure = raw_data.get("micro_structure")
            if ui_metrics and "micro_structure" in ui_metrics:
                micro_structure = ui_metrics["micro_structure"]
        except Exception as exc:
            logger.warning("[L3 Assembler] data extraction failed: %s", exc)
        return fused_signal, micro_structure

    @staticmethod
    def _resolve_data_timestamp(
        source_timestamp: Any,
        signal: SignalData,
        default_now_iso: str,
    ) -> str:
        return to_utc_iso(source_timestamp) or to_utc_iso(signal.computed_at) or default_now_iso

    @staticmethod
    def _resolve_ui_flip_level(snap: SnapshotData) -> float | None:
        level = getattr(snap, "zero_gamma_level", None)
        if level is None:
            return None
        try:
            numeric = float(level)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(numeric) or numeric <= 0.0:
            return None
        return numeric

    def _build_ui_state(
        self,
        snap: SnapshotData,
        active_options: Any,
        *,
        flip_level: float | None,
    ) -> UIState:
        try:
            micro_stats = MicroStatsPresenterV2.build(
                gex_regime=snap.gex_regime,
                wall_dyn=snap.wall_dyn,
                vanna=snap.vanna_state,
                momentum=snap.momentum,
            )
        except Exception as exc:
            logger.warning("[L3 Assembler] MicroStats failed: %s", exc)
            micro_stats = MicroStatsState.zero_state()

        try:
            tactical_triad = TacticalTriadPresenterV2.build(
                vrp=snap.vrp,
                vrp_state=snap.vrp_state,
                net_charm=snap.net_charm,
                svol_corr=snap.svol_corr,
                svol_state=snap.svol_state,
                fused_signal_direction=snap.fused_signal_direction,
            )
        except Exception as exc:
            logger.warning("[L3 Assembler] TacticalTriad failed: %s", exc)
            tactical_triad = TacticalTriadState.zero_state()

        try:
            wall_migration = WallMigrationPresenterV2.build(snap.wall_migration_data)
        except Exception as exc:
            logger.warning("[L3 Assembler] WallMigration failed: %s", exc)
            wall_migration = ()

        try:
            depth_profile = DepthProfilePresenterV2.build(
                per_strike_gex=snap.per_strike_gex,
                spot=snap.spot if snap.spot else None,
                flip_level=flip_level,
            )
        except Exception as exc:
            logger.warning("[L3 Assembler] DepthProfile failed: %s", exc)
            depth_profile = ()

        try:
            if hasattr(active_options, "__iter__"):
                from l3_assembly.events.payload_events import ActiveOptionRow

                active_opts = tuple(
                    row for row in active_options if isinstance(row, ActiveOptionRow)
                ) or tuple(
                    convert_active_option(row)
                    for row in active_options
                    if isinstance(row, dict)
                )
            else:
                active_opts = ()
        except Exception as exc:
            logger.warning("[L3 Assembler] ActiveOptions failed: %s", exc)
            active_opts = ()

        try:
            mtf_flow = MTFFlowPresenterV2.build(snap.mtf_consensus)
        except Exception as exc:
            logger.warning("[L3 Assembler] MTFFlow failed: %s", exc)
            mtf_flow = MTFFlowState.zero_state()

        try:
            skew_dynamics = SkewDynamicsPresenterV2.build(snap.skew_dynamics)
        except Exception as exc:
            logger.warning("[L3 Assembler] SkewDynamics failed: %s", exc)
            skew_dynamics = {}

        try:
            iv_velocity = getattr(snap, "iv_velocity", None)
            if iv_velocity and hasattr(iv_velocity, "model_dump"):
                iv_velocity = iv_velocity.model_dump()
        except Exception as exc:
            logger.warning("[L3 Assembler] IV Velocity fallback failed: %s", exc)
            iv_velocity = None

        return UIState(
            micro_stats=micro_stats,
            tactical_triad=tactical_triad,
            wall_migration=wall_migration,
            depth_profile=depth_profile,
            active_options=active_opts,
            mtf_flow=mtf_flow,
            skew_dynamics=skew_dynamics,
            macro_volume_map=snap.volume_map,
            iv_velocity=iv_velocity,
        )

    @staticmethod
    def _compute_drift(source_timestamp: Any, signal: SignalData) -> tuple[float, bool]:
        try:
            source_iso = to_utc_iso(source_timestamp)
            computed_iso = to_utc_iso(signal.computed_at)
            if not source_iso or not computed_iso:
                return 0.0, False
            delay = (
                datetime.fromisoformat(computed_iso) - datetime.fromisoformat(source_iso)
            ).total_seconds()
            return delay * 1000.0, delay > 0.8
        except Exception as exc:
            logger.warning("[L3 Assembler] Drift calculation failed: %s", exc)
            return 0.0, False

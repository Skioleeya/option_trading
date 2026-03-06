"""l3_assembly.assembly.payload_assembler — PayloadAssemblerV2.

Copy-on-Write assembler that replaces legacy SnapshotBuilder.build().

Key improvements over legacy:
    1. Accepts typed L2 DecisionOutput + L1 EnrichedSnapshot (not raw dicts)
    2. Builds FrozenPayload (immutable) — no deepcopy needed
    3. Calls Presenter V2 wrappers for strong-typed UIState
    4. Drift detection logic encapsulated here (not in _broadcast_loop)
    5. Pure function: no module-level state, fully testable

Legacy schema compatibility:
    FrozenPayload.to_dict() produces the SAME dict that SnapshotBuilder
    previously returned, so the React frontend is unaffected.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from l3_assembly.events.payload_events import (
    FrozenPayload,
    SignalData,
    UIState,
    MicroStatsState,
    TacticalTriadState,
    MTFFlowState,
)
from l3_assembly.presenters.micro_stats import MicroStatsPresenterV2
from l3_assembly.presenters.tactical_triad import TacticalTriadPresenterV2
from l3_assembly.presenters.wall_migration import WallMigrationPresenterV2
from l3_assembly.presenters.depth_profile import DepthProfilePresenterV2
from l3_assembly.presenters.mtf_flow import MTFFlowPresenterV2
from l3_assembly.presenters.skew_dynamics import SkewDynamicsPresenterV2

logger = logging.getLogger(__name__)


class PayloadAssemblerV2:
    """Copy-on-Write payload assembler.

    Usage:
        assembler = PayloadAssemblerV2()
        frozen = assembler.assemble(decision, snapshot, atm_decay, active_options)
        payload_dict = frozen.to_dict()   # backward-compatible with legacy frontend
    """

    def assemble(
        self,
        decision: Any,            # L2 DecisionOutput (typed)
        snapshot: Any,            # L1 EnrichedSnapshot (typed)  OR  legacy dict
        atm_decay: dict[str, Any] | None,
        active_options: Any = None,  # tuple[ActiveOptionRow, ...] or []
        ui_metrics: dict[str, Any] = None,
    ) -> FrozenPayload:
        """Assemble an immutable FrozenPayload from L2+L1 inputs.

        Args:
            decision:       L2 DecisionOutput frozen dataclass.
            snapshot:       L1 EnrichedSnapshot frozen dataclass (or legacy dict).
            atm_decay:      ATM decay dict from AtmDecayTracker (pass-through).
            active_options: Pre-computed active options rows from background loop.

        Returns:
            FrozenPayload — immutable, serialization-ready.
        """
        start = time.monotonic()

        # ── 1. Signal data from L2 decision ────────────────────────────────
        try:
            signal = SignalData.from_decision_output(decision)
        except Exception as exc:
            logger.warning(f"[L3 Assembler] SignalData extraction failed: {exc}")
            signal = SignalData.neutral()

        # ── 2. Extract raw fields for presenters ───────────────────────────
        try:
            snap_data = self._extract_snapshot_data(snapshot, decision, ui_metrics)
        except Exception as exc:
            logger.warning(f"[L3 Assembler] Snapshot extraction failed: {exc}")
            snap_data = _SnapshotData()

        # ── 3. Drift detection ─────────────────────────────────────────────
        drift_ms, drift_warning = self._compute_drift(snap_data.snapshot_time, signal)

        # ── 4. Build UIState via Presenter V2 calls ────────────────────────
        ui_state = self._build_ui_state(snap_data, active_options or ())

        # ── 5. Extract fused_signal & micro_structure from L2/UI sources ──────────
        # AgentG._decide_impl writes fused_signal under AgentResult.data["fused_signal"]
        # and micro_structure under AgentResult.data["micro_structure"].
        # DecisionOutput shim provides 'fused_signal' under decision.data property.
        # Microstructure is now primarily provided via ui_metrics from UIStateTracker.
        fused_signal_dict: dict | None = None
        micro_structure_dict: dict | None = None
        try:
            if decision is not None:
                raw_data = getattr(decision, "data", None) or {}
                fused_signal_dict = raw_data.get("fused_signal")
                # Fallback to decision data, but UI metrics take priority
                micro_structure_dict = raw_data.get("micro_structure")
                
            if ui_metrics and "micro_structure" in ui_metrics:
                micro_structure_dict = ui_metrics["micro_structure"]

        except Exception as exc:
            logger.warning(f"[L3 Assembler] data extraction failed: {exc}")

        # ── 6. Timestamps ─────────────────────────────────────────────────────
        now_iso = datetime.now(timezone.utc).isoformat()

        payload = FrozenPayload(
            data_timestamp=signal.computed_at or now_iso,
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
            gamma_flip_level=snap_data.flip_level,
            fused_signal=fused_signal_dict,
            micro_structure=micro_structure_dict,
            rust_active=snap_data.rust_active,
            shm_stats=snap_data.shm_stats,
        )

        logger.debug(
            f"[L3 Assembler] assembled in {(time.monotonic() - start)*1000:.2f}ms, "
            f"spot={snap_data.spot}, version={signal.version}"
        )
        return payload

    # ── Private helpers ────────────────────────────────────────────────────

    def _extract_snapshot_data(self, snapshot: Any, decision: Any, ui_metrics: dict[str, Any] = None) -> "_SnapshotData":
        """Extract raw display fields from snapshot (supports both typed + legacy dict)."""
        data = _SnapshotData()

        # L1 EnrichedSnapshot (typed)
        if hasattr(snapshot, "spot") and hasattr(snapshot, "aggregates"):
            data.spot = float(snapshot.spot or 0.0)
            data.atm_iv = float(snapshot.aggregates.atm_iv or 0.0)
            data.flip_level = float(snapshot.aggregates.flip_level or 0.0)
            data.snapshot_time = getattr(snapshot, "computed_at", None)
            # Aggregated GEX per strike (legacy presenters expect list[dict])
            data.per_strike_gex = getattr(snapshot.aggregates, "per_strike_gex", [])
            
            data.net_gex = float(snapshot.aggregates.net_gex or 0.0)
            data.call_wall = float(snapshot.aggregates.call_wall or 0.0)
            data.put_wall = float(snapshot.aggregates.put_wall or 0.0)
            
            # Metadata support (Phase 1 fix: Rust status)
            metadata = getattr(snapshot, "extra_metadata", {})
            data.rust_active = bool(metadata.get("rust_active", False))
            data.shm_stats = metadata.get("shm_stats")

        # Legacy dict (from OptionChainBuilder.fetch_chain())
        elif isinstance(snapshot, dict):
            data.spot = float(snapshot.get("spot", 0.0) or 0.0)
            data.atm_iv = float(snapshot.get("atm_iv", snapshot.get("spy_atm_iv", 0.0)) or 0.0)
            data.snapshot_time = snapshot.get("as_of")
            data.volume_map = snapshot.get("volume_map") or {}
            data.net_gex = float(snapshot.get("net_gex", 0.0) or 0.0)
            data.call_wall = float(snapshot.get("call_wall", 0.0) or 0.0)
            data.put_wall = float(snapshot.get("put_wall", 0.0) or 0.0)
            data.flip_level = float(snapshot.get("flip_level", 0.0) or 0.0)
            data.rust_active = bool(snapshot.get("rust_active", False))
            data.shm_stats = snapshot.get("shm_stats")

        # Supplement from L2 decision's data block if available
        if decision is not None:
            try:
                # L2 DecisionOutput (typed) — extract from signal_summary
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
            data.wall_migration_data = ui_metrics.get("wall_migration_data", data.wall_migration_data)
            data.mtf_consensus = ui_metrics.get("mtf_consensus", data.mtf_consensus)
            data.skew_dynamics = ui_metrics.get("skew_dynamics", data.skew_dynamics)
            data.iv_velocity = ui_metrics.get("iv_velocity", data.iv_velocity)

        return data

    def _build_ui_state(
        self,
        snap: "_SnapshotData",
        active_options: Any,
    ) -> UIState:
        """Call all 7 Presenter V2 and assemble UIState."""
        # MicroStats
        try:
            micro_stats = MicroStatsPresenterV2.build(
                gex_regime=snap.gex_regime,
                wall_dyn=snap.wall_dyn,
                vanna=snap.vanna_state,
                momentum=snap.momentum,
            )
        except Exception as exc:
            logger.warning(f"[L3 Assembler] MicroStats failed: {exc}")
            micro_stats = MicroStatsState.zero_state()

        # TacticalTriad
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
            import traceback
            traceback.print_exc()
            logger.warning(f"[L3 Assembler] TacticalTriad failed: {exc}")
            tactical_triad = TacticalTriadState.zero_state()

        # WallMigration
        try:
            wall_migration = WallMigrationPresenterV2.build(snap.wall_migration_data)
        except Exception as exc:
            logger.warning(f"[L3 Assembler] WallMigration failed: {exc}")
            wall_migration = ()

        # DepthProfile
        try:
            depth_profile = DepthProfilePresenterV2.build(
                per_strike_gex=snap.per_strike_gex,
                spot=snap.spot if snap.spot else None,
                flip_level=snap.flip_level if snap.flip_level else None,
            )
        except Exception as exc:
            logger.warning(f"[L3 Assembler] DepthProfile failed: {exc}")
            depth_profile = ()

        # Active Options (already computed in background loop)
        try:
            if hasattr(active_options, '__iter__'):
                from l3_assembly.events.payload_events import ActiveOptionRow
                active_opts = tuple(
                    r for r in active_options
                    if isinstance(r, ActiveOptionRow)
                ) or tuple(
                    # Fallback: raw dicts from legacy presenter
                    _convert_active_option(r) for r in active_options
                    if isinstance(r, dict)
                )
            else:
                active_opts = ()
        except Exception as exc:
            logger.warning(f"[L3 Assembler] ActiveOptions failed: {exc}")
            active_opts = ()

        # MTFFlow
        try:
            mtf_flow = MTFFlowPresenterV2.build(snap.mtf_consensus)
        except Exception as exc:
            logger.warning(f"[L3 Assembler] MTFFlow failed: {exc}")
            mtf_flow = MTFFlowState.zero_state()

        # SkewDynamics
        try:
            skew_dynamics = SkewDynamicsPresenterV2.build(snap.skew_dynamics)
        except Exception as exc:
            logger.warning(f"[L3 Assembler] SkewDynamics failed: {exc}")
            skew_dynamics = {}

        # IV Velocity
        try:
            iv_velocity = getattr(snap, "iv_velocity", None)
            if iv_velocity and hasattr(iv_velocity, "model_dump"):
                iv_velocity = iv_velocity.model_dump()
        except Exception as exc:
            logger.warning(f"[L3 Assembler] IV Velocity fallback failed: {exc}")
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
    def _compute_drift(
        snapshot_time: Any,
        signal: SignalData,
    ) -> tuple[float, bool]:
        """Calculate data drift between L0 snapshot and L2 compute time."""
        try:
            from datetime import datetime
            agent_as_of = datetime.fromisoformat(signal.computed_at.replace("Z", "+00:00"))

            if isinstance(snapshot_time, datetime):
                snap_dt = snapshot_time
            elif isinstance(snapshot_time, str):
                snap_dt = datetime.fromisoformat(snapshot_time)
            else:
                return 0.0, False

            delay = (agent_as_of - snap_dt).total_seconds()
            drift_ms = delay * 1000
            return drift_ms, delay > 0.8
        except Exception:
            return 0.0, False


# ─────────────────────────────────────────────────────────────────────────────
# Internal snapshot data container
# ─────────────────────────────────────────────────────────────────────────────

class _SnapshotData:
    """Mutable accumulator for extracted snapshot fields.

    Used internally by PayloadAssemblerV2._extract_snapshot_data().
    Not exposed as a public API.
    """
    __slots__ = (
        "spot", "atm_iv", "flip_level", "snapshot_time", "gex_regime", "vanna_state",
        "momentum", "vrp", "vrp_state", "net_charm", "svol_corr", "svol_state",
        "fused_signal_direction", "wall_dyn", "wall_migration_data",
        "per_strike_gex", "mtf_consensus", "skew_dynamics", "volume_map",
        "net_gex", "call_wall", "put_wall", "iv_velocity",
        "rust_active", "shm_stats",
    )

    def __init__(self) -> None:
        self.spot: float = 0.0
        self.atm_iv: float = 0.0
        self.flip_level: float = 0.0
        self.snapshot_time: Any = None
        self.gex_regime: str = "NEUTRAL"
        self.vanna_state: str = "NORMAL"
        self.momentum: str = "NEUTRAL"
        self.vrp: float | None = None
        self.vrp_state: str | None = None
        self.net_charm: float | None = None
        self.svol_corr: float | None = None
        self.svol_state: str | None = None
        self.fused_signal_direction: str | None = None
        self.wall_dyn: dict = {}
        self.wall_migration_data: dict = {}
        self.per_strike_gex: list = []
        self.mtf_consensus: dict = {}
        self.skew_dynamics: dict = {}
        self.volume_map: dict = {}
        self.net_gex: float = 0.0
        self.call_wall: float = 0.0
        self.put_wall: float = 0.0
        self.iv_velocity: dict | None = None
        self.rust_active: bool = False
        self.shm_stats: dict | None = None


def _convert_active_option(d: dict) -> Any:
    """Convert legacy dict row to ActiveOptionRow (best-effort)."""
    from l3_assembly.events.payload_events import ActiveOptionRow
    return ActiveOptionRow(
        symbol=str(d.get("symbol", "SPY")),
        option_type=str(d.get("option_type", "C")),
        strike=float(d.get("strike", 0.0) or 0.0),
        implied_volatility=float(d.get("implied_volatility", 0.0) or 0.0),
        volume=int(d.get("volume", 0) or 0),
        turnover=float(d.get("turnover", 0.0) or 0.0),
        flow=float(d.get("flow", 0.0) or 0.0),
        flow_deg_formatted=str(d.get("flow_deg_formatted", "$0")),
        flow_volume_label=str(d.get("flow_volume_label", "0")),
        flow_color=str(d.get("flow_color", "text-text-secondary")),
        flow_glow=str(d.get("flow_glow", "")),
        flow_intensity=str(d.get("flow_intensity", "LOW")),
        flow_direction=str(d.get("flow_direction", "NEUTRAL")),
        flow_d_z=float(d.get("flow_d_z", 0.0) or 0.0),
        flow_e_z=float(d.get("flow_e_z", 0.0) or 0.0),
        flow_g_z=float(d.get("flow_g_z", 0.0) or 0.0),
    )

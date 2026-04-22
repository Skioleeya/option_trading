import type { DashboardState } from './dashboardStore'

/** Selector: full payload (for backward-compat App.tsx shim) */
export const selectPayload = (s: DashboardState) => s.payload

/** Selector: connection status */
export const selectConnectionStatus = (s: DashboardState) =>
    s.connectionStatus

/** Selector: spot price */
export const selectSpot = (s: DashboardState) => s.spot

/** Selector: iv% */
export const selectIvPct = (s: DashboardState) => s.ivPct

export const selectHeaderVolatility = (s: DashboardState) => s.headerVolatility

/** Selector: ATM decay (latest tick) */
export const selectAtm = (s: DashboardState) => s.atm

/** Selector: ATM history (chart data) */
export const selectAtmHistory = (s: DashboardState) => s.atmHistory

/** Selector: ui_state sub-tree */
export const selectUiState = (s: DashboardState) =>
    s.payload?.agent_g?.data?.ui_state ?? null

export const selectUiStateMicroStats = (s: DashboardState) =>
    s.payload?.agent_g?.data?.ui_state?.micro_stats ?? null

export const selectUiStateWallMigration = (s: DashboardState) =>
    s.payload?.agent_g?.data?.ui_state?.wall_migration ?? null

export const selectUiStateDepthProfile = (s: DashboardState) =>
    s.payload?.agent_g?.data?.ui_state?.depth_profile ?? null

export const selectUiStateMacroVolumeMap = (s: DashboardState) =>
    s.payload?.agent_g?.data?.ui_state?.macro_volume_map ?? null

export const selectUiStateActiveOptions = (s: DashboardState) =>
    s.payload?.agent_g?.data?.ui_state?.active_options ?? null

export const selectUiStateTacticalTriad = (s: DashboardState) =>
    s.payload?.agent_g?.data?.ui_state?.tactical_triad ?? null

export const selectUiStateSkewDynamics = (s: DashboardState) =>
    s.payload?.agent_g?.data?.ui_state?.skew_dynamics ?? null

export const selectUiStateMtfFlow = (s: DashboardState) =>
    s.payload?.agent_g?.data?.ui_state?.mtf_flow ?? null

export const selectUiStateIvVelocity = (s: DashboardState) =>
    s.payload?.agent_g?.data?.ui_state?.iv_velocity ?? null

export const selectPayloadTimestamp = (s: DashboardState) =>
    s.payload?.timestamp ?? null

export const selectFusedIvRegime = (s: DashboardState) =>
    s.payload?.agent_g?.data?.fused_signal?.iv_regime ?? 'NORMAL'

export const selectRustActive = (s: DashboardState) =>
    s.payload?.rust_active ?? null

export const selectPayloadVersion = (s: DashboardState) =>
    s.payloadVersion

export const selectBroadcastTimestamp = (s: DashboardState) =>
    s.broadcastTimestamp

export const selectDriftMs = (s: DashboardState) =>
    s.driftMs

export const selectDriftWarning = (s: DashboardState) =>
    s.driftWarning

export const selectIsStale = (s: DashboardState) =>
    s.isStale

/** Selector: fused signal */
export const selectFused = (s: DashboardState) =>
    s.payload?.agent_g?.data?.fused_signal ?? null

/** Selector: net_gex */
export const selectNetGex = (s: DashboardState) =>
    s.payload?.agent_g?.data?.net_gex ?? null

/** Selector: gamma walls */
export const selectGammaWalls = (s: DashboardState) =>
    s.payload?.agent_g?.data?.gamma_walls ?? null

/** Selector: gamma flip level */
export const selectFlipLevel = (s: DashboardState) =>
    s.payload?.agent_g?.data?.gamma_flip_level ?? null

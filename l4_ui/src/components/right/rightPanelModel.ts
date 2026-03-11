import type {
    ActiveOption,
    DashboardPayload,
    FusedSignal,
    MtfFlowState,
    SkewDynamicsState,
    TacticalTriadState,
} from '../../types/dashboard'

export interface NetGexBadgeState {
    label: string
    badge: string
}

export interface RightPanelContracts {
    fused: FusedSignal | null
    netGex: NetGexBadgeState | null
    tacticalTriad: TacticalTriadState | null
    skewDynamics: SkewDynamicsState | null
    mtfFlow: MtfFlowState | null
    activeOptions: ActiveOption[] | null
}

export function deriveRightPanelContracts(payload: DashboardPayload | null): RightPanelContracts {
    const data = payload?.agent_g?.data
    const uiState = data?.ui_state

    return {
        fused: data?.fused_signal ?? null,
        netGex: uiState?.micro_stats?.net_gex ?? null,
        tacticalTriad: uiState?.tactical_triad ?? null,
        skewDynamics: uiState?.skew_dynamics ?? null,
        mtfFlow: uiState?.mtf_flow ?? null,
        activeOptions: uiState?.active_options ?? null,
    }
}

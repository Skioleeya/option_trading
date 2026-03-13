import type {
    ActiveOption,
    DashboardPayload,
    FusedSignal,
    SkewDynamicsState,
    TacticalTriadState,
} from '../../types/dashboard'
import { normalizeActiveOptions } from './activeOptionsModel'
import { ACTIVE_OPTIONS_FIXED_ROWS } from './activeOptionsTheme'
import { normalizeMtfFlowState, type MtfFlowViewState } from './mtfFlowModel'
import { normalizeSkewDynamicsState } from './skewDynamicsModel'
import { normalizeTacticalTriadState } from './tacticalTriadModel'

export interface NetGexBadgeState {
    label: string
    badge: string
}

export interface RightPanelContracts {
    fused: FusedSignal | null
    netGex: NetGexBadgeState | null
    tacticalTriad: TacticalTriadState
    skewDynamics: SkewDynamicsState
    mtfFlow: MtfFlowViewState
    activeOptions: ActiveOption[]
}

export const RIGHT_PANEL_ACTIVE_OPTION_ROWS = ACTIVE_OPTIONS_FIXED_ROWS

const RIGHT_PANEL_BADGE_WHITELIST = new Set<string>([
    'badge-neutral',
    'badge-amber',
    'badge-red',
    'badge-green',
    'badge-purple',
    'badge-cyan',
    'badge-hollow-purple',
    'badge-hollow-amber',
    'badge-hollow-cyan',
    'badge-hollow-green',
    'badge-red-dim',
])

function normalizeNetGexBadge(input: unknown): NetGexBadgeState | null {
    if (!input || typeof input !== 'object') return null
    const raw = input as Partial<NetGexBadgeState>
    const label = typeof raw.label === 'string' ? raw.label.trim() : ''
    if (!label) return null

    const badge = typeof raw.badge === 'string' && RIGHT_PANEL_BADGE_WHITELIST.has(raw.badge)
        ? raw.badge
        : 'badge-neutral'

    return {
        label,
        badge,
    }
}

export function deriveRightPanelContracts(payload: DashboardPayload | null): RightPanelContracts {
    const data = payload?.agent_g?.data
    const uiState = data?.ui_state

    return {
        fused: data?.fused_signal ?? null,
        netGex: normalizeNetGexBadge(uiState?.micro_stats?.net_gex ?? null),
        tacticalTriad: normalizeTacticalTriadState(uiState?.tactical_triad ?? null),
        skewDynamics: normalizeSkewDynamicsState(uiState?.skew_dynamics ?? null),
        mtfFlow: normalizeMtfFlowState(uiState?.mtf_flow ?? null),
        activeOptions: normalizeActiveOptions(uiState?.active_options ?? [], RIGHT_PANEL_ACTIVE_OPTION_ROWS),
    }
}

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

export interface RawVannaCardState {
    value: string
    exactValue: string
    stateLabel: 'POSITIVE' | 'NEGATIVE' | 'FLAT' | 'UNAVAILABLE'
    colorClass: string
    borderClass: string
    bgClass: string
    badgeClass: string
}

export interface RightPanelContracts {
    fused: FusedSignal | null
    netGex: NetGexBadgeState | null
    rawVanna: RawVannaCardState
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

export const RAW_VANNA_ZERO: RawVannaCardState = {
    value: '—',
    exactValue: '—',
    stateLabel: 'UNAVAILABLE',
    colorClass: 'text-text-secondary',
    borderClass: 'border-bg-border',
    bgClass: 'bg-bg-card',
    badgeClass: 'badge-neutral',
}

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

function formatSigned(value: number, digits: number): string {
    const abs = Math.abs(value)
    const rendered = abs.toLocaleString('en-US', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    })
    if (value > 0) return `+${rendered}`
    if (value < 0) return `-${rendered}`
    return rendered
}

function formatCompactSigned(value: number): string {
    const abs = Math.abs(value)
    if (abs >= 1_000_000_000) return `${value > 0 ? '+' : '-'}${(abs / 1_000_000_000).toFixed(2)}B`
    if (abs >= 1_000_000) return `${value > 0 ? '+' : '-'}${(abs / 1_000_000).toFixed(2)}M`
    if (abs >= 1_000) return `${value > 0 ? '+' : '-'}${(abs / 1_000).toFixed(2)}K`
    if (value === 0) return '0.0000'
    return formatSigned(value, abs >= 100 ? 2 : abs >= 1 ? 3 : 4)
}

function normalizeRawVanna(input: unknown): RawVannaCardState {
    if (typeof input !== 'number' || !Number.isFinite(input)) {
        return RAW_VANNA_ZERO
    }

    const abs = Math.abs(input)
    if (abs < 1e-9) {
        return {
            value: '0.0000',
            exactValue: '0.0000',
            stateLabel: 'FLAT',
            colorClass: 'text-text-primary',
            borderClass: 'border-bg-border',
            bgClass: 'bg-bg-card',
            badgeClass: 'badge-neutral',
        }
    }

    if (input > 0) {
        return {
            value: formatCompactSigned(input),
            exactValue: formatSigned(input, abs >= 1_000 ? 2 : 4),
            stateLabel: 'POSITIVE',
            colorClass: 'text-accent-cyan',
            borderClass: 'border-accent-cyan/40',
            bgClass: 'bg-accent-cyan/5',
            badgeClass: 'badge-hollow-cyan',
        }
    }

    return {
        value: formatCompactSigned(input),
        exactValue: formatSigned(input, abs >= 1_000 ? 2 : 4),
        stateLabel: 'NEGATIVE',
        colorClass: 'text-accent-amber',
        borderClass: 'border-accent-amber/40',
        bgClass: 'bg-accent-amber/5',
        badgeClass: 'badge-hollow-amber',
    }
}

export function deriveRightPanelContracts(payload: DashboardPayload | null): RightPanelContracts {
    const data = payload?.agent_g?.data
    const uiState = data?.ui_state
    const rawVanna = data?.micro_structure?.micro_structure_state?.net_vanna_raw_sum ?? null

    return {
        fused: data?.fused_signal ?? null,
        netGex: normalizeNetGexBadge(uiState?.micro_stats?.net_gex ?? null),
        rawVanna: normalizeRawVanna(rawVanna),
        tacticalTriad: normalizeTacticalTriadState(uiState?.tactical_triad ?? null),
        skewDynamics: normalizeSkewDynamicsState(uiState?.skew_dynamics ?? null),
        mtfFlow: normalizeMtfFlowState(uiState?.mtf_flow ?? null),
        activeOptions: normalizeActiveOptions(uiState?.active_options ?? [], RIGHT_PANEL_ACTIVE_OPTION_ROWS),
    }
}

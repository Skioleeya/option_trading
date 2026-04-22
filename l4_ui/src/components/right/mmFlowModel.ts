import type { DashboardPayload } from '../../types/dashboard'

export interface MmFlowMetrics {
    net_delta_exposure_live: number
    net_gamma_exposure_live: number
    residual_delta_after_netting: number
    oi_participation_ratio_live: number
    flow_suppression_bias: number
    flow_dominance_ratio: number
    midpoint_tickrule_count: number
    condition_filtered_count: number
    complex_spread_count: number
}

export interface MmFlowView {
    directionLabel: 'SUPPRESSIVE' | 'EXPANSIVE' | 'BALANCED'
    netDelta: string
    netGamma: string
    residualDelta: string
    dominanceRatio: string
    oiParticipation: string
    suppressionBias: string
    midpointCount: string
    filteredCount: string
    spreadCount: string
}

function finite(value: unknown, fallback = 0): number {
    return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function signed(value: number, digits: number): string {
    if (!Number.isFinite(value)) return '0'
    const abs = Math.abs(value).toLocaleString('en-US', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    })
    if (value > 0) return `+${abs}`
    if (value < 0) return `-${abs}`
    return abs
}

function compactSigned(value: number): string {
    const abs = Math.abs(value)
    if (abs >= 1_000_000_000) return `${value >= 0 ? '+' : '-'}${(abs / 1_000_000_000).toFixed(2)}B`
    if (abs >= 1_000_000) return `${value >= 0 ? '+' : '-'}${(abs / 1_000_000).toFixed(2)}M`
    if (abs >= 1_000) return `${value >= 0 ? '+' : '-'}${(abs / 1_000).toFixed(2)}K`
    return signed(value, 2)
}

function ratioPct(value: number): string {
    return `${(value * 100).toFixed(1)}%`
}

export function readMmFlowCandidate(payload: DashboardPayload | null): Record<string, unknown> | null {
    const data = payload?.agent_g?.data as Record<string, unknown> | undefined
    if (!data) return null
    const explicit = data.mm_flow
    if (explicit && typeof explicit === 'object') return explicit as Record<string, unknown>
    const fused = data.fused_signal
    if (fused && typeof fused === 'object') {
        const fromFused = (fused as Record<string, unknown>).mm_flow
        if (fromFused && typeof fromFused === 'object') {
            return fromFused as Record<string, unknown>
        }
    }
    return null
}

export function deriveMmFlowMetricsFromCandidate(raw: Record<string, unknown> | null): MmFlowMetrics | null {
    if (!raw) return null
    return {
        net_delta_exposure_live: finite(raw.net_delta_exposure_live, 0),
        net_gamma_exposure_live: finite(raw.net_gamma_exposure_live, 0),
        residual_delta_after_netting: finite(raw.residual_delta_after_netting, 0),
        oi_participation_ratio_live: finite(raw.oi_participation_ratio_live, 0),
        flow_suppression_bias: finite(raw.flow_suppression_bias, 0),
        flow_dominance_ratio: finite(raw.flow_dominance_ratio, 0),
        midpoint_tickrule_count: finite(raw.midpoint_tickrule_count, 0),
        condition_filtered_count: finite(raw.condition_filtered_count, 0),
        complex_spread_count: finite(raw.complex_spread_count, 0),
    }
}


export function deriveMmFlowMetrics(payload: DashboardPayload | null): MmFlowMetrics | null {
    return deriveMmFlowMetricsFromCandidate(readMmFlowCandidate(payload))
}

export function deriveMmFlowView(metrics: MmFlowMetrics | null): MmFlowView | null {
    if (!metrics) return null
    const dominance = metrics.flow_dominance_ratio
    const directionLabel: MmFlowView['directionLabel'] =
        dominance > 0.05 ? 'SUPPRESSIVE' : dominance < -0.05 ? 'EXPANSIVE' : 'BALANCED'

    return {
        directionLabel,
        netDelta: compactSigned(metrics.net_delta_exposure_live),
        netGamma: compactSigned(metrics.net_gamma_exposure_live),
        residualDelta: compactSigned(metrics.residual_delta_after_netting),
        dominanceRatio: ratioPct(metrics.flow_dominance_ratio),
        oiParticipation: ratioPct(metrics.oi_participation_ratio_live),
        suppressionBias: compactSigned(metrics.flow_suppression_bias),
        midpointCount: signed(metrics.midpoint_tickrule_count, 0),
        filteredCount: signed(metrics.condition_filtered_count, 0),
        spreadCount: signed(metrics.complex_spread_count, 0),
    }
}

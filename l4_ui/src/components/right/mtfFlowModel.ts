import type { MtfFlowState, MtfTfState } from '../../types/dashboard'

export const DEFAULT_TF: MtfTfState = {
    direction: 'NEUTRAL',
    regime: 'NOISE',
    regime_label: '—',
    z: 0,
    strength: 0,
    tier: 'WEAK',
    dot_color: 'bg-zinc-700',
    text_color: 'text-text-secondary',
    shadow: 'shadow-none',
    border: 'border-bg-border',
    animate: '',
}

export const DEFAULT_MTF_FLOW_STATE: MtfFlowState = {
    m1: { ...DEFAULT_TF },
    m5: { ...DEFAULT_TF },
    m15: { ...DEFAULT_TF },
    consensus: 'NEUTRAL',
    strength: 0,
    alignment: 0,
    align_label: 'DIVERGE',
    align_color: 'text-text-secondary',
}

function toFiniteNumber(raw: unknown, fallback = 0): number {
    const value = typeof raw === 'number' ? raw : Number(raw)
    return Number.isFinite(value) ? value : fallback
}

function clamp01(value: number): number {
    if (value < 0) return 0
    if (value > 1) return 1
    return value
}

function normalizeConsensus(raw: unknown): 'BULLISH' | 'BEARISH' | 'NEUTRAL' {
    const text = typeof raw === 'string' ? raw.trim().toUpperCase() : ''
    if (text === 'BULLISH' || text === 'BEARISH') return text
    return 'NEUTRAL'
}

function normalizeTfState(raw: unknown): MtfTfState {
    if (!raw || typeof raw !== 'object') return { ...DEFAULT_TF }
    const src = raw as Partial<MtfTfState>
    const strength = clamp01(toFiniteNumber(src.strength, DEFAULT_TF.strength))
    return {
        direction: typeof src.direction === 'string' && src.direction.trim() ? src.direction : DEFAULT_TF.direction,
        regime: typeof src.regime === 'string' && src.regime.trim() ? src.regime : DEFAULT_TF.regime,
        regime_label: typeof src.regime_label === 'string' && src.regime_label.trim() ? src.regime_label : DEFAULT_TF.regime_label,
        z: toFiniteNumber(src.z, DEFAULT_TF.z),
        strength,
        tier: typeof src.tier === 'string' && src.tier.trim() ? src.tier : DEFAULT_TF.tier,
        dot_color: typeof src.dot_color === 'string' && src.dot_color.trim() ? src.dot_color : DEFAULT_TF.dot_color,
        text_color: typeof src.text_color === 'string' && src.text_color.trim() ? src.text_color : DEFAULT_TF.text_color,
        shadow: typeof src.shadow === 'string' && src.shadow.trim() ? src.shadow : DEFAULT_TF.shadow,
        border: typeof src.border === 'string' && src.border.trim() ? src.border : DEFAULT_TF.border,
        animate: typeof src.animate === 'string' ? src.animate : DEFAULT_TF.animate,
    }
}

function resolveAlignColor(label: string, consensus: 'BULLISH' | 'BEARISH' | 'NEUTRAL'): string {
    if (label === 'ALIGNED') {
        if (consensus === 'BULLISH') return 'text-accent-red'
        if (consensus === 'BEARISH') return 'text-accent-green'
        return 'text-text-secondary'
    }
    if (label === 'SPLIT') return 'text-accent-amber'
    return 'text-text-secondary'
}

export function normalizeMtfFlowState(input: unknown): MtfFlowState {
    if (!input || typeof input !== 'object') return { ...DEFAULT_MTF_FLOW_STATE }
    const src = input as Partial<MtfFlowState>
    const consensus = normalizeConsensus(src.consensus)
    const strength = clamp01(toFiniteNumber(src.strength, DEFAULT_MTF_FLOW_STATE.strength))
    const alignment = clamp01(toFiniteNumber(src.alignment, DEFAULT_MTF_FLOW_STATE.alignment))
    const alignLabelRaw = typeof src.align_label === 'string' ? src.align_label.trim() : ''
    const align_label = alignLabelRaw || (alignment >= 0.67 ? 'ALIGNED' : alignment >= 0.34 ? 'SPLIT' : 'DIVERGE')
    const align_color =
        typeof src.align_color === 'string' && src.align_color.trim()
            ? src.align_color
            : resolveAlignColor(align_label, consensus)

    return {
        m1: normalizeTfState(src.m1),
        m5: normalizeTfState(src.m5),
        m15: normalizeTfState(src.m15),
        consensus,
        strength,
        alignment,
        align_label,
        align_color,
    }
}

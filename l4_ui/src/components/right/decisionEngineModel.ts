import type { FusedSignal } from '../../types/dashboard'

export type DecisionTone = 'BULLISH' | 'BEARISH' | 'NEUTRAL' | 'HALT'

type DirectionClasses = {
    dot: string
    bar: string
    text: string
    banner: string
}

const DIRECTION_ALIASES: Record<string, DecisionTone> = {
    BULLISH: 'BULLISH',
    BEARISH: 'BEARISH',
    NEUTRAL: 'NEUTRAL',
    HALT: 'HALT',
    LOW_VOL: 'BULLISH',
    HIGH_VOL: 'BEARISH',
    NORMAL: 'NEUTRAL',
}

const DIRECTION_CLASSES: Record<DecisionTone, DirectionClasses> = {
    BULLISH: {
        dot: 'bg-accent-red shadow-[0_0_6px_rgba(255,77,79,0.5)]',
        bar: 'bg-accent-red',
        text: 'text-accent-red',
        banner: 'bg-red-950/40 border-red-500/30',
    },
    BEARISH: {
        dot: 'bg-accent-green shadow-[0_0_6px_rgba(0,214,143,0.5)]',
        bar: 'bg-accent-green',
        text: 'text-accent-green',
        banner: 'bg-emerald-950/40 border-emerald-500/30',
    },
    NEUTRAL: {
        dot: 'bg-zinc-600',
        bar: 'bg-zinc-600',
        text: 'text-text-secondary',
        banner: 'bg-zinc-900/40 border-zinc-700/30',
    },
    HALT: {
        dot: 'bg-accent-amber shadow-[0_0_8px_rgba(245,158,11,0.6)] animate-pulse',
        bar: 'bg-accent-amber',
        text: 'text-accent-amber',
        banner: 'bg-amber-950/50 border-amber-500/40',
    },
}

function finiteNumber(value: unknown): number | null {
    return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function normalizeDecisionTone(direction: unknown): DecisionTone {
    const key = String(direction ?? '').trim().toUpperCase()
    return DIRECTION_ALIASES[key] ?? 'NEUTRAL'
}

export function resolveDirectionClasses(tone: DecisionTone): DirectionClasses {
    return DIRECTION_CLASSES[tone] ?? DIRECTION_CLASSES.NEUTRAL
}

export function ratioToPercent(value: unknown): number {
    const n = finiteNumber(value)
    if (n === null) return 0
    return Math.max(0, Math.min(100, Math.round(n * 100)))
}

export function confidenceToPercent(value: unknown): number {
    return ratioToPercent(value)
}

export function formatRegimeLabel(value: unknown): string {
    const raw = String(value ?? '').trim()
    if (!raw) return ''

    const noUnderscore = raw.replace(/_/g, ' ')
    const spaced = noUnderscore.toUpperCase() === noUnderscore
        ? noUnderscore
        : noUnderscore.replace(/([a-z0-9])([A-Z])/g, '$1 $2')

    return spaced.replace(/\s+/g, ' ').trim().toUpperCase()
}

export function resolveWeightPercent(
    fused: FusedSignal | null | undefined,
    componentKey: string,
): number {
    const weights = fused?.weights as Record<string, unknown> | undefined
    const fromWeights = finiteNumber(weights?.[componentKey])
    if (fromWeights !== null) return ratioToPercent(fromWeights)

    const components = fused?.components as Record<string, unknown> | undefined
    const rawComp = components?.[componentKey]
    const comp = rawComp && typeof rawComp === 'object' ? (rawComp as Record<string, unknown>) : null
    const fromCompWeight = finiteNumber(comp?.weight)
    if (fromCompWeight !== null) return ratioToPercent(fromCompWeight)

    return 0
}

export function resolveWeightBarWidth(percent: number): number {
    if (percent <= 0) return 0
    return Math.max(percent, 2)
}

export function resolveGexIntensityBadgeClass(gexIntensity: unknown): string {
    const label = String(gexIntensity ?? '').toUpperCase()
    if (label.includes('NEGATIVE')) return 'badge-red-dim'
    if (label.includes('POSITIVE')) return 'badge-hollow-green'
    if (label.includes('MODERATE')) return 'badge-amber'
    return 'badge-neutral'
}

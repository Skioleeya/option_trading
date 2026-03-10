import type { ActiveOption } from '../../types/dashboard'

export function normalizeOptionType(raw: unknown): 'CALL' | 'PUT' {
    const text = typeof raw === 'string' ? raw.trim().toUpperCase() : ''
    return text === 'CALL' || text === 'C' ? 'CALL' : 'PUT'
}

export type ActiveFlowDirection = 'BULLISH' | 'BEARISH' | 'NEUTRAL'
export type ActiveFlowIntensity = 'EXTREME' | 'HIGH' | 'MODERATE' | 'LOW'

const ASIAN_FLOW_COLOR_BY_DIRECTION: Record<ActiveFlowDirection, string> = {
    BULLISH: 'text-accent-red',
    BEARISH: 'text-accent-green',
    NEUTRAL: 'text-text-secondary',
}

const ALLOWED_FLOW_COLOR = new Set<string>([
    'text-accent-red',
    'text-accent-green',
    'text-text-secondary',
])

const FLOW_DIRECTION_BY_COLOR: Record<string, ActiveFlowDirection> = {
    'text-accent-red': 'BULLISH',
    'text-accent-green': 'BEARISH',
    'text-text-secondary': 'NEUTRAL',
}

function createPlaceholderOption(slotIndex: number): ActiveOption {
    return {
        symbol: '—',
        option_type: 'CALL',
        strike: 0,
        implied_volatility: 0,
        volume: 0,
        turnover: 0,
        flow: 0,
        flow_score: 0,
        impact_index: 0,
        is_sweep: false,
        flow_deg_formatted: '—',
        flow_volume_label: '—',
        flow_color: 'text-text-secondary',
        flow_glow: '',
        flow_intensity: 'LOW',
        flow_direction: 'NEUTRAL',
        is_placeholder: true,
        slot_index: Math.max(1, slotIndex),
    }
}

function parseCompactNumber(raw: string): number | null {
    const text = raw.trim()
    if (!text) return null

    const accountingNegative = text.startsWith('(') && text.endsWith(')')
    const sanitized = text
        .replace(/[()]/g, '')
        .replace(/\s+/g, '')
        .replace(/\$/g, '')
        .replace(/,/g, '')
        .toUpperCase()

    const match = sanitized.match(/^([+-]?\d*\.?\d+)([KMBT])?$/)
    if (!match) return null

    const value = Number(match[1])
    if (!Number.isFinite(value)) return null

    const unit = match[2] ?? ''
    const multiplier = unit === 'K' ? 1e3
        : unit === 'M' ? 1e6
            : unit === 'B' ? 1e9
                : unit === 'T' ? 1e12
                    : 1
    const signed = accountingNegative ? -Math.abs(value) : value
    return signed * multiplier
}

function toFiniteNumber(raw: unknown, fallback = 0): number {
    if (typeof raw === 'number') {
        return Number.isFinite(raw) ? raw : fallback
    }
    if (typeof raw === 'string') {
        const numeric = Number(raw)
        if (Number.isFinite(numeric)) return numeric
        const compact = parseCompactNumber(raw)
        if (compact !== null && Number.isFinite(compact)) return compact
    }
    return fallback
}

function toFiniteInteger(raw: unknown, fallback = 0): number {
    return Math.max(0, Math.trunc(toFiniteNumber(raw, fallback)))
}

function normalizeFlowDirection(flow: number): ActiveFlowDirection {
    if (flow > 0) return 'BULLISH'
    if (flow < 0) return 'BEARISH'
    return 'NEUTRAL'
}

function normalizeFlowIntensity(raw: unknown): ActiveFlowIntensity {
    const text = typeof raw === 'string' ? raw.trim().toUpperCase() : ''
    if (text === 'EXTREME' || text === 'HIGH' || text === 'MODERATE' || text === 'LOW') {
        return text
    }
    return 'LOW'
}

function normalizeFlowColor(raw: unknown, direction: ActiveFlowDirection): string {
    const text = typeof raw === 'string' ? raw.trim() : ''
    if (text && ALLOWED_FLOW_COLOR.has(text) && FLOW_DIRECTION_BY_COLOR[text] === direction) {
        return text
    }
    return ASIAN_FLOW_COLOR_BY_DIRECTION[direction]
}

export function normalizeActiveOption(input: unknown): ActiveOption {
    const row = (input && typeof input === 'object') ? (input as Partial<ActiveOption>) : {}
    const isPlaceholder = Boolean(row.is_placeholder)
    const slotIndexRaw = toFiniteInteger(row.slot_index, 0)
    const slotIndex = slotIndexRaw > 0 ? slotIndexRaw : undefined

    if (isPlaceholder) {
        return createPlaceholderOption(slotIndex ?? 1)
    }

    const isSweep = Boolean(row.is_sweep)
    const flowFromLabel = toFiniteNumber(row.flow_deg_formatted, 0)
    const flow = toFiniteNumber(row.flow, flowFromLabel)
    const flowDirection = normalizeFlowDirection(flow)
    const flowIntensity = normalizeFlowIntensity(row.flow_intensity)
    const flowColor = normalizeFlowColor(row.flow_color, flowDirection)
    const flowScore = toFiniteNumber(row.flow_score, 0)
    const normalizedGlow = typeof row.flow_glow === 'string' && row.flow_glow.trim()
        ? row.flow_glow
        : (isSweep ? 'shadow-[0_0_15px_rgba(255,255,255,0.7)] animate-pulse' : '')

    return {
        symbol: typeof row.symbol === 'string' && row.symbol.trim() ? row.symbol : 'SPY',
        option_type: normalizeOptionType(row.option_type),
        strike: toFiniteNumber(row.strike, 0),
        implied_volatility: Math.max(0, toFiniteNumber(row.implied_volatility, 0)),
        volume: toFiniteInteger(row.volume, 0),
        turnover: Math.max(0, toFiniteNumber(row.turnover, 0)),
        flow,
        flow_score: flowScore,
        impact_index: toFiniteNumber(row.impact_index, 0),
        is_sweep: isSweep,
        flow_deg_formatted: typeof row.flow_deg_formatted === 'string' ? row.flow_deg_formatted : undefined,
        flow_volume_label: typeof row.flow_volume_label === 'string' ? row.flow_volume_label : undefined,
        flow_color: flowColor,
        flow_glow: normalizedGlow,
        flow_intensity: flowIntensity,
        flow_direction: flowDirection,
        is_placeholder: false,
        slot_index: slotIndex,
    }
}

export function normalizeActiveOptions(input: unknown, limit = 5): ActiveOption[] {
    const target = Math.max(0, limit)
    const source = Array.isArray(input) ? input : []
    const normalized = source
        .map((row) => normalizeActiveOption(row))
        .slice(0, target)
        .map((row, idx) => ({
            ...row,
            slot_index: idx + 1,
        }))

    while (normalized.length < target) {
        normalized.push(createPlaceholderOption(normalized.length + 1))
    }
    return normalized
}

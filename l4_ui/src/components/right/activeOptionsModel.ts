import type { ActiveOption } from '../../types/dashboard'
import {
    ACTIVE_OPTIONS_FIXED_ROWS,
    ACTIVE_OPTIONS_ALLOWED_FLOW_COLOR,
    ACTIVE_OPTIONS_FLOW_COLOR_BY_DIRECTION,
    ACTIVE_OPTIONS_FLOW_DIRECTION_BY_COLOR,
    ACTIVE_OPTIONS_FLOW_GLOW_BY_DIRECTION_AND_INTENSITY,
    ACTIVE_OPTIONS_FLOW_INTENSITY_SET,
    ACTIVE_OPTIONS_SWEEP_GLOW,
    type ActiveFlowDirection,
    type ActiveFlowIntensity,
} from './activeOptionsTheme'

export function normalizeOptionType(raw: unknown): 'CALL' | 'PUT' {
    const text = typeof raw === 'string' ? raw.trim().toUpperCase() : ''
    return text === 'CALL' || text === 'C' ? 'CALL' : 'PUT'
}

export type { ActiveFlowDirection, ActiveFlowIntensity } from './activeOptionsTheme'

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
    if (ACTIVE_OPTIONS_FLOW_INTENSITY_SET.has(text)) {
        return text as ActiveFlowIntensity
    }
    return 'LOW'
}

function normalizeFlowColor(raw: unknown, direction: ActiveFlowDirection): string {
    const text = typeof raw === 'string' ? raw.trim() : ''
    if (text && ACTIVE_OPTIONS_ALLOWED_FLOW_COLOR.has(text) && ACTIVE_OPTIONS_FLOW_DIRECTION_BY_COLOR[text] === direction) {
        return text
    }
    return ACTIVE_OPTIONS_FLOW_COLOR_BY_DIRECTION[direction]
}

function normalizeFlowDisplayLabel(raw: unknown, flow: number): string | undefined {
    const text = typeof raw === 'string' ? raw.trim() : ''
    if (!text) return undefined
    const parsed = parseCompactNumber(text)
    if (parsed === null) return text

    // For neutral flow, avoid signed zero text like "-$0".
    if (flow === 0) return '$0'
    // If backend display text conflicts with numeric sign, discard and let UI format from normalized flow.
    if ((flow > 0 && parsed < 0) || (flow < 0 && parsed > 0)) {
        return undefined
    }
    return text
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
    const normalizedGlow = isSweep
        ? ACTIVE_OPTIONS_SWEEP_GLOW
        : ACTIVE_OPTIONS_FLOW_GLOW_BY_DIRECTION_AND_INTENSITY[flowDirection][flowIntensity]

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
        flow_deg_formatted: normalizeFlowDisplayLabel(row.flow_deg_formatted, flow),
        flow_volume_label: typeof row.flow_volume_label === 'string' ? row.flow_volume_label : undefined,
        flow_color: flowColor,
        flow_glow: normalizedGlow,
        flow_intensity: flowIntensity,
        flow_direction: flowDirection,
        is_placeholder: false,
        slot_index: slotIndex,
    }
}

export function normalizeActiveOptions(input: unknown, limit = ACTIVE_OPTIONS_FIXED_ROWS): ActiveOption[] {
    const target = Math.max(0, limit)
    const source = Array.isArray(input) ? input : []
    const ranked = source
        .map((item, idx) => ({
            row: normalizeActiveOption(item),
            idx,
        }))
        .sort((a, b) => {
            const aPlaceholder = Boolean(a.row.is_placeholder)
            const bPlaceholder = Boolean(b.row.is_placeholder)
            if (aPlaceholder !== bPlaceholder) return aPlaceholder ? 1 : -1

            const volumeDiff = b.row.volume - a.row.volume
            if (volumeDiff !== 0) return volumeDiff

            const turnoverDiff = b.row.turnover - a.row.turnover
            if (turnoverDiff !== 0) return turnoverDiff

            const impactA = typeof a.row.impact_index === 'number' ? a.row.impact_index : 0
            const impactB = typeof b.row.impact_index === 'number' ? b.row.impact_index : 0
            const impactDiff = impactB - impactA
            if (impactDiff !== 0) return impactDiff

            return a.idx - b.idx
        })

    const normalized: ActiveOption[] = ranked
        .slice(0, target)
        .map(({ row }, idx) => ({
            ...row,
            slot_index: idx + 1,
        }))

    while (normalized.length < target) {
        normalized.push(createPlaceholderOption(normalized.length + 1))
    }
    return normalized
}

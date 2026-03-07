import type { ActiveOption } from '../../types/dashboard'

export function normalizeOptionType(raw: unknown): 'CALL' | 'PUT' {
    const text = typeof raw === 'string' ? raw.trim().toUpperCase() : ''
    return text === 'CALL' || text === 'C' ? 'CALL' : 'PUT'
}

function toFiniteNumber(raw: unknown, fallback = 0): number {
    const value = typeof raw === 'number' ? raw : Number(raw)
    return Number.isFinite(value) ? value : fallback
}

function toFiniteInteger(raw: unknown, fallback = 0): number {
    return Math.max(0, Math.trunc(toFiniteNumber(raw, fallback)))
}

export function normalizeActiveOption(input: unknown): ActiveOption {
    const row = (input && typeof input === 'object') ? (input as Partial<ActiveOption>) : {}
    const isSweep = Boolean(row.is_sweep)
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
        flow: toFiniteNumber(row.flow, 0),
        impact_index: toFiniteNumber(row.impact_index, 0),
        is_sweep: isSweep,
        flow_deg_formatted: typeof row.flow_deg_formatted === 'string' ? row.flow_deg_formatted : undefined,
        flow_volume_label: typeof row.flow_volume_label === 'string' ? row.flow_volume_label : undefined,
        flow_color: typeof row.flow_color === 'string' ? row.flow_color : undefined,
        flow_glow: normalizedGlow,
        flow_intensity: row.flow_intensity,
        flow_direction: row.flow_direction,
    }
}

export function normalizeActiveOptions(input: unknown, limit = 5): ActiveOption[] {
    if (!Array.isArray(input)) return []
    return input
        .map((row) => normalizeActiveOption(row))
        .slice(0, Math.max(0, limit))
}


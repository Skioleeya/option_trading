export type ChartEngineKey = 'lightweight'

export interface L4FeatureFlags {
    centerV2: boolean
    rightV2: boolean
    leftV2: boolean
}

export interface L4RuntimeConfig {
    wsUrl: string
    apiBase: string
    chartEngine: ChartEngineKey
    flags: L4FeatureFlags
}

const DEFAULT_WS_URL = 'ws://localhost:8001/ws/dashboard'
const DEFAULT_API_BASE = 'http://localhost:8001'

function parseBoolean(raw: unknown, fallback: boolean): boolean {
    if (typeof raw === 'boolean') return raw
    if (typeof raw !== 'string') return fallback
    const normalized = raw.trim().toLowerCase()
    if (normalized === '1' || normalized === 'true' || normalized === 'yes' || normalized === 'on') {
        return true
    }
    if (normalized === '0' || normalized === 'false' || normalized === 'no' || normalized === 'off') {
        return false
    }
    return fallback
}

function parseChartEngine(raw: unknown): ChartEngineKey {
    if (typeof raw !== 'string') return 'lightweight'
    return raw.trim().toLowerCase() === 'lightweight' ? 'lightweight' : 'lightweight'
}

function normalizeApiBase(raw: unknown): string {
    const base = typeof raw === 'string' && raw.trim() ? raw.trim() : DEFAULT_API_BASE
    return base.endsWith('/') ? base.slice(0, -1) : base
}

export const runtimeConfig: L4RuntimeConfig = {
    wsUrl: typeof import.meta.env.VITE_L4_WS_URL === 'string' && import.meta.env.VITE_L4_WS_URL.trim()
        ? import.meta.env.VITE_L4_WS_URL.trim()
        : DEFAULT_WS_URL,
    apiBase: normalizeApiBase(import.meta.env.VITE_L4_API_BASE),
    chartEngine: parseChartEngine(import.meta.env.VITE_L4_CHART_ENGINE),
    flags: {
        centerV2: parseBoolean(import.meta.env.VITE_L4_ENABLE_CENTER_V2, true),
        rightV2: parseBoolean(import.meta.env.VITE_L4_ENABLE_RIGHT_V2, true),
        leftV2: parseBoolean(import.meta.env.VITE_L4_ENABLE_LEFT_V2, true),
    },
}

export type ChartEngineKey = 'lightweight'

export interface L4FeatureFlags {
    centerV2: boolean
    rightV2: boolean
    leftV2: boolean
}

export interface L4RuntimeConfig {
    backendOrigin: string
    wsUrl: string
    apiBase: string
    chartEngine: ChartEngineKey
    flags: L4FeatureFlags
}

type RuntimeEnv = Record<string, unknown>
type RuntimeProcessEnv = Record<string, string | undefined>
type BrowserLocation = { protocol: string; host: string }

function readProcessEnv(): RuntimeProcessEnv | null {
    const candidate = (globalThis as { process?: { env?: RuntimeProcessEnv } }).process?.env
    return candidate ?? null
}

function resolveRuntimeEnv(importMetaEnv: RuntimeEnv): RuntimeEnv {
    const resolved: RuntimeEnv = { ...importMetaEnv }
    const processEnv = readProcessEnv()
    if (!processEnv) return resolved

    const processOrigin = typeof processEnv.VITE_BACKEND_ORIGIN === 'string'
        ? processEnv.VITE_BACKEND_ORIGIN.trim()
        : ''
    const importOrigin = typeof resolved.VITE_BACKEND_ORIGIN === 'string'
        ? resolved.VITE_BACKEND_ORIGIN.trim()
        : ''

    if (!importOrigin && processOrigin) {
        resolved.VITE_BACKEND_ORIGIN = processOrigin
    }

    if (typeof processEnv.VITE_L4_API_BASE === 'string' && processEnv.VITE_L4_API_BASE.trim()) {
        resolved.VITE_L4_API_BASE = processEnv.VITE_L4_API_BASE.trim()
    }
    if (typeof processEnv.VITE_L4_WS_URL === 'string' && processEnv.VITE_L4_WS_URL.trim()) {
        resolved.VITE_L4_WS_URL = processEnv.VITE_L4_WS_URL.trim()
    }
    return resolved
}

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

function readBrowserLocation(): BrowserLocation | null {
    const candidate = (globalThis as { location?: { protocol?: unknown; host?: unknown } }).location
    if (!candidate) return null
    if (typeof candidate.protocol !== 'string' || typeof candidate.host !== 'string') return null
    if (!candidate.protocol || !candidate.host) return null
    return { protocol: candidate.protocol, host: candidate.host }
}

function assertLegacyVarsForbidden(env: RuntimeEnv): void {
    const legacyApi = typeof env.VITE_L4_API_BASE === 'string' ? env.VITE_L4_API_BASE.trim() : ''
    const legacyWs = typeof env.VITE_L4_WS_URL === 'string' ? env.VITE_L4_WS_URL.trim() : ''
    if (legacyApi || legacyWs) {
        throw new Error(
            '[L4 Runtime] legacy endpoint vars are forbidden. Use VITE_BACKEND_ORIGIN only.'
        )
    }
}

function normalizeBackendOrigin(raw: unknown): string {
    if (typeof raw !== 'string' || !raw.trim()) {
        throw new Error('[L4 Runtime] VITE_BACKEND_ORIGIN is required (e.g. http://127.0.0.1:8001).')
    }

    let parsed: URL
    try {
        parsed = new URL(raw.trim())
    } catch {
        throw new Error(`[L4 Runtime] invalid VITE_BACKEND_ORIGIN: ${String(raw)}`)
    }

    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        throw new Error(
            `[L4 Runtime] VITE_BACKEND_ORIGIN must use http/https, got ${parsed.protocol}`
        )
    }
    if (!parsed.hostname) {
        throw new Error('[L4 Runtime] VITE_BACKEND_ORIGIN must include hostname.')
    }
    if (parsed.pathname !== '/' || parsed.search || parsed.hash) {
        throw new Error(
            '[L4 Runtime] VITE_BACKEND_ORIGIN must be origin-only (no path/query/hash).'
        )
    }

    return parsed.origin
}

function buildWsUrl(backendOrigin: string): string {
    const parsed = new URL(backendOrigin)
    const wsProtocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsProtocol}//${parsed.host}/ws/dashboard`
}

function buildBrowserWsUrl(location: BrowserLocation): string {
    const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsProtocol}//${location.host}/ws/dashboard`
}

export function buildRuntimeConfig(
    env: RuntimeEnv,
    options?: { location?: BrowserLocation | null }
): L4RuntimeConfig {
    assertLegacyVarsForbidden(env)
    const backendOrigin = normalizeBackendOrigin(env.VITE_BACKEND_ORIGIN)
    const location = options?.location === undefined ? readBrowserLocation() : options.location
    const browserFacing = Boolean(location)
    return {
        backendOrigin,
        wsUrl: browserFacing ? buildBrowserWsUrl(location as BrowserLocation) : buildWsUrl(backendOrigin),
        apiBase: browserFacing ? '' : backendOrigin,
        chartEngine: parseChartEngine(env.VITE_L4_CHART_ENGINE),
        flags: {
            centerV2: parseBoolean(env.VITE_L4_ENABLE_CENTER_V2, true),
            rightV2: parseBoolean(env.VITE_L4_ENABLE_RIGHT_V2, true),
            leftV2: parseBoolean(env.VITE_L4_ENABLE_LEFT_V2, true),
        },
    }
}

export const runtimeConfig: L4RuntimeConfig = buildRuntimeConfig(
    resolveRuntimeEnv(import.meta.env as unknown as RuntimeEnv)
)

export const __runtimeTestOnly = {
    normalizeBackendOrigin,
    buildWsUrl,
    buildBrowserWsUrl,
    assertLegacyVarsForbidden,
    resolveRuntimeEnv,
    readBrowserLocation,
}

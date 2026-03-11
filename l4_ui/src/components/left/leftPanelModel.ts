import type { DashboardPayload } from '../../types/dashboard'

export interface LeftWallMigrationRow {
    label: string
    strike: number | null
    state: string
    history: number[]
    lights?: Record<string, string>
}

export interface LeftDepthProfileRow {
    strike: number
    put_pct: number
    call_pct: number
    is_dominant_put: boolean
    is_dominant_call: boolean
    is_spot: boolean
    is_flip: boolean
}

export interface LeftMicroStats {
    net_gex: { label: string; badge: string }
    wall_dyn: { label: string; badge: string }
    vanna: { label: string; badge: string }
    momentum: { label: string; badge: string }
}

export interface LeftPanelContracts {
    spot: number | null
    gammaWalls: { call_wall: number | null; put_wall: number | null } | null
    flipLevel: number | null
    wallMigrationRows: LeftWallMigrationRow[]
    depthProfileRows: LeftDepthProfileRow[]
    macroVolumeMap: Record<string, number>
    microStats: LeftMicroStats | null
}

function toFiniteNumber(raw: unknown, fallback = 0): number {
    const value = typeof raw === 'number' ? raw : Number(raw)
    return Number.isFinite(value) ? value : fallback
}

function toOptionalFiniteNumber(raw: unknown): number | null {
    const value = typeof raw === 'number' ? raw : Number(raw)
    return Number.isFinite(value) ? value : null
}

function toBoolean(raw: unknown): boolean {
    return raw === true || raw === 'true' || raw === 1 || raw === '1'
}

function normalizeWallMigrationRows(raw: unknown): LeftWallMigrationRow[] {
    if (!Array.isArray(raw)) return []
    return raw.map((row): LeftWallMigrationRow => {
        const src = row && typeof row === 'object' ? (row as Record<string, unknown>) : {}
        return {
            label: typeof src.type_label === 'string' ? src.type_label : '—',
            strike: toOptionalFiniteNumber(src.current),
            state: typeof src.state === 'string'
                ? src.state
                : (typeof src.type_label === 'string' ? src.type_label : 'UNAVAILABLE'),
            history: [
                toFiniteNumber(src.h1, 0),
                toFiniteNumber(src.h2, 0),
            ],
            lights: null,
        }
    })
}

function normalizeDepthProfileRows(raw: unknown): LeftDepthProfileRow[] {
    if (!Array.isArray(raw)) return []
    return raw
        .map((row): LeftDepthProfileRow | null => {
            const src = row && typeof row === 'object' ? (row as Record<string, unknown>) : {}
            const strike = toFiniteNumber(src.strike, Number.NaN)
            if (!Number.isFinite(strike)) return null
            return {
                strike,
                put_pct: Math.max(0, toFiniteNumber(src.put_pct, 0)),
                call_pct: Math.max(0, toFiniteNumber(src.call_pct, 0)),
                is_dominant_put: toBoolean(src.is_dominant_put),
                is_dominant_call: toBoolean(src.is_dominant_call),
                is_spot: toBoolean(src.is_spot),
                is_flip: toBoolean(src.is_flip),
            }
        })
        .filter((row): row is LeftDepthProfileRow => row !== null)
}

function normalizeMacroVolumeMap(raw: unknown): Record<string, number> {
    if (!raw || typeof raw !== 'object') return {}
    const out: Record<string, number> = {}
    for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
        const parsed = toFiniteNumber(value, Number.NaN)
        if (Number.isFinite(parsed)) {
            out[key] = parsed
        }
    }
    return out
}

function normalizeMicroStats(raw: unknown): LeftMicroStats | null {
    if (!raw || typeof raw !== 'object') return null
    const src = raw as Record<string, unknown>
    const normalizeCell = (cell: unknown) => {
        const c = cell && typeof cell === 'object' ? (cell as Record<string, unknown>) : {}
        return {
            label: typeof c.label === 'string' ? c.label : '—',
            badge: typeof c.badge === 'string' ? c.badge : 'badge-neutral',
        }
    }
    return {
        net_gex: normalizeCell(src.net_gex),
        wall_dyn: normalizeCell(src.wall_dyn),
        vanna: normalizeCell(src.vanna),
        momentum: normalizeCell(src.momentum),
    }
}

export function deriveLeftPanelContracts(payload: DashboardPayload | null): LeftPanelContracts {
    const data = payload?.agent_g?.data
    const uiState = data?.ui_state
    const gammaWalls = data?.gamma_walls ?? null

    return {
        spot: payload?.spot ?? null,
        gammaWalls: gammaWalls
            ? {
                call_wall: toOptionalFiniteNumber(gammaWalls.call_wall),
                put_wall: toOptionalFiniteNumber(gammaWalls.put_wall),
            }
            : null,
        flipLevel: toOptionalFiniteNumber(data?.gamma_flip_level),
        wallMigrationRows: normalizeWallMigrationRows(uiState?.wall_migration),
        depthProfileRows: normalizeDepthProfileRows(uiState?.depth_profile),
        macroVolumeMap: normalizeMacroVolumeMap(uiState?.macro_volume_map),
        microStats: normalizeMicroStats(uiState?.micro_stats),
    }
}

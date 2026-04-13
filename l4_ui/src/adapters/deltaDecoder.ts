/**
 * l4_ui — DeltaDecoder (Phase 1: Protocol & State Decoupling)
 * ──────────────────────────────────────────────────────────────────
 * Isolated, side-effect-free JSON-Patch decoder.
 */

import { applyPatch } from 'fast-json-patch'
import type { DashboardPayload } from '../types/dashboard'

export type DecodeResult<T> =
    | { ok: true; value: T }
    | { ok: false; error: unknown }

const FLOW_DIRECTION = new Set(['BULLISH', 'BEARISH', 'NEUTRAL'])
const FLOW_INTENSITY = new Set(['EXTREME', 'HIGH', 'MODERATE', 'LOW'])
const FLOW_COLOR = new Set(['text-accent-red', 'text-accent-green', 'text-text-secondary'])
const FLOW_DIRECTION_BY_COLOR: Record<string, string> = {
    'text-accent-red': 'BULLISH',
    'text-accent-green': 'BEARISH',
    'text-text-secondary': 'NEUTRAL',
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null
}

function requireFiniteNumber(record: Record<string, unknown>, key: keyof DashboardPayload): number {
    const value = record[key as string]
    if (typeof value !== 'number' || !Number.isFinite(value)) {
        throw new Error(`[L4 Contract] ${String(key)} must be a finite number`)
    }
    return value
}

function requireString(record: Record<string, unknown>, key: keyof DashboardPayload): string {
    const value = record[key as string]
    if (typeof value !== 'string' || value.trim() === '') {
        throw new Error(`[L4 Contract] ${String(key)} must be a non-empty string`)
    }
    return value
}

function requireBoolean(record: Record<string, unknown>, key: keyof DashboardPayload): boolean {
    const value = record[key as string]
    if (typeof value !== 'boolean') {
        throw new Error(`[L4 Contract] ${String(key)} must be boolean`)
    }
    return value
}

function validateActiveOptionsRows(payload: DashboardPayload): void {
    const rows = payload.agent_g?.data?.ui_state?.active_options
    if (rows == null) return
    if (!Array.isArray(rows)) {
        throw new Error('[L4 Contract] ui_state.active_options must be an array or null')
    }
    // Premarket / no-qualified-flow windows can legitimately produce 0 rows.
    // UI model normalizes to fixed 5 render slots via placeholders.
    if (rows.length > 5) {
        throw new Error(`[L4 Contract] ui_state.active_options must contain at most 5 rows, got ${rows.length}`)
    }

    for (const row of rows) {
        if (!isRecord(row)) {
            throw new Error('[L4 Contract] active_options row must be object')
        }
        if (Boolean(row.is_placeholder)) {
            continue
        }

        const direction = String(row.flow_direction ?? '').toUpperCase()
        const intensity = String(row.flow_intensity ?? '').toUpperCase()
        const color = String(row.flow_color ?? '')
        const glow = row.flow_glow

        if (!FLOW_DIRECTION.has(direction)) {
            throw new Error(`[L4 Contract] invalid flow_direction: ${String(row.flow_direction)}`)
        }
        if (!FLOW_INTENSITY.has(intensity)) {
            throw new Error(`[L4 Contract] invalid flow_intensity: ${String(row.flow_intensity)}`)
        }
        if (!FLOW_COLOR.has(color)) {
            throw new Error(`[L4 Contract] invalid flow_color: ${String(row.flow_color)}`)
        }
        if (FLOW_DIRECTION_BY_COLOR[color] !== direction) {
            throw new Error('[L4 Contract] flow_color and flow_direction mismatch')
        }
        if (typeof glow !== 'string') {
            throw new Error('[L4 Contract] flow_glow must be string')
        }

        const flow = row.flow
        if (typeof flow !== 'number' || !Number.isFinite(flow)) {
            throw new Error('[L4 Contract] flow must be finite number')
        }
        if (flow > 0 && direction !== 'BULLISH') {
            throw new Error('[L4 Contract] positive flow requires BULLISH direction')
        }
        if (flow < 0 && direction !== 'BEARISH') {
            throw new Error('[L4 Contract] negative flow requires BEARISH direction')
        }
        if (flow === 0 && direction !== 'NEUTRAL') {
            throw new Error('[L4 Contract] zero flow requires NEUTRAL direction')
        }
    }
}

function validatePayloadStrict(payload: unknown): DashboardPayload {
    if (!isRecord(payload)) {
        throw new Error('[L4 Contract] payload must be object')
    }

    requireFiniteNumber(payload, 'version')
    requireString(payload, 'data_timestamp')
    requireString(payload, 'broadcast_timestamp')
    requireString(payload, 'timestamp')
    requireString(payload, 'heartbeat_timestamp')
    requireFiniteNumber(payload, 'spot')
    requireFiniteNumber(payload, 'drift_ms')
    requireBoolean(payload, 'drift_warning')
    requireBoolean(payload, 'is_stale')
    requireBoolean(payload, 'rust_active')

    if (!isRecord(payload.shm_stats)) {
        throw new Error('[L4 Contract] shm_stats must be object')
    }
    if (typeof payload.shm_stats.status !== 'string' || payload.shm_stats.status.trim() === '') {
        throw new Error('[L4 Contract] shm_stats.status must be a non-empty string')
    }
    if (!('head' in payload.shm_stats) || !('tail' in payload.shm_stats)) {
        throw new Error('[L4 Contract] shm_stats.head/tail must be present')
    }
    if ((payload as Record<string, unknown>).timestamp !== (payload as Record<string, unknown>).data_timestamp) {
        throw new Error('[L4 Contract] timestamp must equal data_timestamp')
    }

    validateActiveOptionsRows(payload as DashboardPayload)
    return payload as DashboardPayload
}

export const DeltaDecoder = {
    validatePayload(payload: unknown): DecodeResult<DashboardPayload> {
        try {
            return { ok: true, value: validatePayloadStrict(payload) }
        } catch (error) {
            return { ok: false, error }
        }
    },

    applyPatch(
        prev: DashboardPayload,
        patch: unknown[],
        meta?: {
            heartbeat_timestamp?: string
            timestamp?: string
            broadcast_timestamp?: string
            version?: number
        }
    ): DecodeResult<DashboardPayload> {
        try {
            const prevClone: DashboardPayload = JSON.parse(JSON.stringify(prev))
            const result = applyPatch(prevClone, patch as any, false, true)
            const next = result.newDocument as DashboardPayload

            const withMeta: DashboardPayload = {
                ...next,
                ...(meta?.heartbeat_timestamp !== undefined
                    ? { heartbeat_timestamp: meta.heartbeat_timestamp }
                    : {}),
                ...(meta?.timestamp !== undefined ? { timestamp: meta.timestamp } : {}),
                ...(meta?.broadcast_timestamp !== undefined
                    ? { broadcast_timestamp: meta.broadcast_timestamp }
                    : {}),
                ...(meta?.version !== undefined ? { version: meta.version } : {}),
            }
            if (meta?.timestamp !== undefined) {
                withMeta.data_timestamp = meta.timestamp
            }

            return this.validatePayload(withMeta)
        } catch (error) {
            return { ok: false, error }
        }
    },

    applyChanges(
        prev: DashboardPayload,
        changes: Record<string, any>,
        meta?: {
            heartbeat_timestamp?: string
            timestamp?: string
            broadcast_timestamp?: string
            version?: number
        }
    ): DecodeResult<DashboardPayload> {
        const tStart = performance.now()
        try {
            const next: DashboardPayload = { ...prev }

            if (changes.signal && next.agent_g?.data) {
                next.agent_g = {
                    ...next.agent_g,
                    data: {
                        ...next.agent_g.data,
                        ...changes.signal,
                    },
                }
            }

            if (changes.agent_g_ui_state && next.agent_g?.data?.ui_state) {
                next.agent_g = {
                    ...next.agent_g,
                    data: {
                        ...(next.agent_g?.data ?? {}),
                        ui_state: {
                            ...next.agent_g?.data?.ui_state,
                            ...changes.agent_g_ui_state,
                        },
                    },
                }
            }

            if (changes.agent_g_data && next.agent_g?.data) {
                next.agent_g = {
                    ...next.agent_g,
                    data: {
                        ...next.agent_g.data,
                        ...changes.agent_g_data,
                    },
                }
            }

            if (changes.atm !== undefined) {
                next.atm = changes.atm
            }

            const topLevel = [
                'spot',
                'drift_ms',
                'drift_warning',
                'is_stale',
                'version',
                'data_timestamp',
                'broadcast_timestamp',
                'heartbeat_timestamp',
                'rust_active',
                'shm_stats',
            ]
            for (const key of topLevel) {
                if (changes[key] !== undefined) {
                    ; (next as any)[key] = changes[key]
                }
            }

            if (meta?.heartbeat_timestamp !== undefined) next.heartbeat_timestamp = meta.heartbeat_timestamp
            if (meta?.timestamp !== undefined) {
                next.timestamp = meta.timestamp
                next.data_timestamp = meta.timestamp
            }
            if (meta?.broadcast_timestamp !== undefined) next.broadcast_timestamp = meta.broadcast_timestamp
            if (meta?.version !== undefined) next.version = meta.version
            if (changes.data_timestamp !== undefined) next.timestamp = String(changes.data_timestamp)

            const tEnd = performance.now()
            if (tEnd - tStart > 5) {
                console.debug(`[L4 DeltaDecoder] Latency spike: ${(tEnd - tStart).toFixed(2)}ms`)
            }

            return this.validatePayload(next)
        } catch (error) {
            console.error('[L4 DeltaDecoder] Decoding failed:', error)
            return { ok: false, error }
        }
    },

    parseMessage(raw: string): unknown | null {
        try {
            return JSON.parse(raw)
        } catch {
            return null
        }
    },

    isKeepalive(msg: unknown): boolean {
        return (
            msg !== null &&
            typeof msg === 'object' &&
            (msg as any).type === 'keepalive'
        )
    },

    isDelta(msg: unknown): boolean {
        return (
            msg !== null &&
            typeof msg === 'object' &&
            (msg as any).type === 'dashboard_delta'
        )
    },
} as const

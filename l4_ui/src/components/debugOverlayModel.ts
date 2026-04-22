import type { DashboardPayload, ConnectionStatus } from '../types/dashboard'
import { L4Rum } from '../observability/l4_rum'

export interface DebugOverlayModel {
    vpin: string
    bbo: string
    volAccel: string
    asOf: string
    payloadVersion: string
    broadcastTs: string
    driftMs: string
    driftWarning: string
    isStale: string
    connStatus: string
    shmStatus: string
    shmHead: string
    shmTail: string
    shmLag: string
    quoteMode: string
    sourceGapMs: string
    sourceEvents1s: string
    distinctSpots1s: string
    wireLagMs: string
    msgToStoreMs: string
    storeToPaintMs: string
    sourceToPaintMs: string
}

function toNumber(v: unknown): number | null {
    if (typeof v === 'number' && Number.isFinite(v)) return v
    if (typeof v === 'string' && v.trim()) {
        const parsed = Number(v)
        if (Number.isFinite(parsed)) return parsed
    }
    return null
}

function formatRawValue(v: unknown): string {
    if (typeof v === 'number') {
        if (!Number.isFinite(v)) return 'N/A'
        return Number.isInteger(v) ? String(v) : v.toFixed(4).replace(/\.?0+$/, '')
    }
    if (typeof v === 'string' && v.trim()) return v
    return 'N/A'
}

function formatPointer(v: number | null): string {
    return v == null ? 'N/A' : String(Math.trunc(v))
}

function formatBoolean(v: unknown): string {
    if (typeof v !== 'boolean') return 'N/A'
    return v ? 'true' : 'false'
}

function parseShm(payload: DashboardPayload | null): {
    status: string
    head: number | null
    tail: number | null
    lag: number | null
} {
    const shm = payload?.shm_stats
    const statusRaw = shm && typeof shm === 'object' ? (shm as Record<string, unknown>).status : null
    const status = typeof statusRaw === 'string' && statusRaw.trim()
        ? statusRaw
        : payload?.rust_active
            ? 'ONLINE'
            : 'DISCONNECTED'

    const headRaw = shm && typeof shm === 'object' ? (shm as Record<string, unknown>).head : null
    const tailRaw = shm && typeof shm === 'object' ? (shm as Record<string, unknown>).tail : null
    const head = toNumber(headRaw)
    const tail = toNumber(tailRaw)
    const lag = head != null && tail != null ? head - tail : null
    return { status, head, tail, lag }
}

export function buildDebugOverlayModel(
    payload: DashboardPayload | null,
    connStatus: ConnectionStatus
): DebugOverlayModel {
    const fused = payload?.agent_g?.data?.fused_signal
    const shm = parseShm(payload)
    const quoteLane = payload?.governor_telemetry && typeof payload.governor_telemetry === 'object'
        ? (payload.governor_telemetry as Record<string, unknown>).quote_lane as Record<string, unknown> | undefined
        : undefined
    const rum = L4Rum.snapshot()

    return {
        vpin: formatRawValue(fused?.raw_vpin),
        bbo: formatRawValue(fused?.raw_bbo_imb),
        volAccel: formatRawValue(fused?.raw_vol_accel),
        asOf: payload?.timestamp ?? 'Syncing...',
        payloadVersion: formatRawValue(payload?.version),
        broadcastTs: typeof payload?.broadcast_timestamp === 'string' ? payload.broadcast_timestamp : 'N/A',
        driftMs: formatRawValue(payload?.drift_ms),
        driftWarning: formatBoolean(payload?.drift_warning),
        isStale: formatBoolean(payload?.is_stale),
        connStatus: connStatus.toUpperCase(),
        shmStatus: shm.status,
        shmHead: formatPointer(shm.head),
        shmTail: formatPointer(shm.tail),
        shmLag: formatPointer(shm.lag),
        quoteMode: formatRawValue(quoteLane?.mode),
        sourceGapMs: formatRawValue(quoteLane?.last_source_gap_ms),
        sourceEvents1s: formatRawValue(quoteLane?.source_event_count_1s),
        distinctSpots1s: formatRawValue(quoteLane?.distinct_spot_count_1s),
        wireLagMs: formatRawValue(rum.lastWireLagMs),
        msgToStoreMs: formatRawValue(rum.lastMsgLatencyMs),
        storeToPaintMs: formatRawValue(rum.lastStoreToPaintMs),
        sourceToPaintMs: formatRawValue(rum.lastSourceToPaintObservedMs),
    }
}

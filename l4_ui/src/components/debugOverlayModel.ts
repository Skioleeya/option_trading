import type { DashboardPayload, ConnectionStatus } from '../types/dashboard'

export interface DebugOverlayModel {
    vpin: string
    bbo: string
    volAccel: string
    asOf: string
    connStatus: string
    shmStatus: string
    shmHead: string
    shmTail: string
    shmLag: string
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

    return {
        vpin: formatRawValue(fused?.raw_vpin),
        bbo: formatRawValue(fused?.raw_bbo_imb),
        volAccel: formatRawValue(fused?.raw_vol_accel),
        asOf: payload?.timestamp ?? 'Syncing...',
        connStatus: connStatus.toUpperCase(),
        shmStatus: shm.status,
        shmHead: formatPointer(shm.head),
        shmTail: formatPointer(shm.tail),
        shmLag: formatPointer(shm.lag),
    }
}

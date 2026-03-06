import type { ConnectionStatus } from '../../types/dashboard'

export type MarketStatus = 'OPEN' | 'CLOSE'

const ET_TZ = 'America/New_York'
const OPEN_MINUTES = 9 * 60 + 30
const CLOSE_MINUTES = 16 * 60

function getEtParts(now: Date): { weekday: string; minutes: number } {
    const parts = new Intl.DateTimeFormat('en-US', {
        timeZone: ET_TZ,
        hour12: false,
        weekday: 'short',
        hour: '2-digit',
        minute: '2-digit',
    }).formatToParts(now)

    const weekday = parts.find((p) => p.type === 'weekday')?.value ?? 'Sun'
    const hour = Number(parts.find((p) => p.type === 'hour')?.value ?? '0')
    const minute = Number(parts.find((p) => p.type === 'minute')?.value ?? '0')
    return { weekday, minutes: hour * 60 + minute }
}

export function deriveMarketStatus(now: Date = new Date()): MarketStatus {
    const { weekday, minutes } = getEtParts(now)
    if (weekday === 'Sat' || weekday === 'Sun') {
        return 'CLOSE'
    }
    return minutes >= OPEN_MINUTES && minutes < CLOSE_MINUTES ? 'OPEN' : 'CLOSE'
}

export function getConnectionDotClass(status: ConnectionStatus): string {
    if (status === 'connected') return 'bg-[#10b981]'
    if (status === 'connecting') return 'bg-[#f59e0b]'
    if (status === 'stalled') return 'bg-[#f97316]'
    return 'bg-[#ef4444]'
}

export function getConnectionLabel(status: ConnectionStatus): string {
    if (status === 'stalled') return 'RDS STALLED'
    if (status === 'connected') return 'RDS LIVE'
    if (status === 'connecting') return 'RDS SYNC'
    return 'RDS DOWN'
}

export function getRustIndicator(
    rustActive: boolean | null | undefined
): { dotClass: string; label: string } {
    if (rustActive === true) {
        return {
            dotClass: 'bg-[#10b981] shadow-[0_0_8px_rgba(16,185,129,0.6)]',
            label: 'RUST',
        }
    }
    if (rustActive === false) {
        return {
            dotClass: 'bg-[#f97316] shadow-[0_0_8px_rgba(249,115,22,0.55)]',
            label: 'PY FALLBACK',
        }
    }
    return {
        dotClass: 'bg-[#52525b] shadow-[0_0_8px_rgba(113,113,122,0.4)]',
        label: 'RUST ?',
    }
}

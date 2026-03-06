/**
 * ATM decay time helpers.
 *
 * Keep this module pure and tiny so it can be unit-tested independently
 * from chart rendering.
 */

const ET_TIME_ZONE = 'America/New_York'
const MARKET_OPEN_SEC = 9 * 3600 + 30 * 60
const MARKET_CLOSE_SEC = 16 * 3600

const ET_HMS_FORMATTER = new Intl.DateTimeFormat('en-US', {
    timeZone: ET_TIME_ZONE,
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
})

function toDate(ts: string): Date | null {
    const d = new Date(ts)
    if (Number.isNaN(d.getTime())) return null
    return d
}

function getEtHms(date: Date): { hh: number; mm: number; ss: number } | null {
    const parts = ET_HMS_FORMATTER.formatToParts(date)
    const hh = Number(parts.find((p) => p.type === 'hour')?.value)
    const mm = Number(parts.find((p) => p.type === 'minute')?.value)
    const ss = Number(parts.find((p) => p.type === 'second')?.value)
    if (!Number.isFinite(hh) || !Number.isFinite(mm) || !Number.isFinite(ss)) {
        return null
    }
    return { hh, mm, ss }
}

function getSecondsFromEtMidnight(ts: string): number | null {
    const d = toDate(ts)
    if (!d) return null
    const hms = getEtHms(d)
    if (!hms) return null
    return hms.hh * 3600 + hms.mm * 60 + hms.ss
}

export function getHHMM(ts: string): number | null {
    const d = toDate(ts)
    if (!d) return null
    const hms = getEtHms(d)
    if (!hms) return null
    return hms.hh * 100 + hms.mm
}

export function isMarketHours(ts: string): boolean {
    const t = getSecondsFromEtMidnight(ts)
    return t !== null && t >= MARKET_OPEN_SEC && t <= MARKET_CLOSE_SEC
}

export function toUnixSec(ts: string): number | null {
    const d = toDate(ts)
    if (!d) return null
    const ms = d.getTime()
    if (!Number.isFinite(ms)) return null
    return Math.floor(ms / 1000)
}

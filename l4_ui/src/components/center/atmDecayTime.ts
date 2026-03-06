/**
 * ATM decay time helpers.
 *
 * Keep this module pure and tiny so it can be unit-tested independently
 * from chart rendering.
 */

const MARKET_OPEN_SEC = 9 * 3600 + 25 * 60
const MARKET_CLOSE_SEC = 16 * 3600

export function getHHMM(ts: string): number | null {
    const m = ts.match(/T(\d{2}):(\d{2})/)
    if (!m) return null
    return parseInt(m[1], 10) * 100 + parseInt(m[2], 10)
}

function getSecondsFromMidnight(ts: string): number | null {
    const m = ts.match(/T(\d{2}):(\d{2})(?::(\d{2}))?/)
    if (!m) return null
    const hh = parseInt(m[1], 10)
    const mm = parseInt(m[2], 10)
    const ss = m[3] ? parseInt(m[3], 10) : 0
    return hh * 3600 + mm * 60 + ss
}

export function isMarketHours(ts: string): boolean {
    const t = getSecondsFromMidnight(ts)
    return t !== null && t >= MARKET_OPEN_SEC && t <= MARKET_CLOSE_SEC
}

export function toUnixSec(ts: string): number | null {
    const ms = new Date(ts).getTime()
    if (!Number.isFinite(ms)) return null
    return Math.floor(ms / 1000)
}

import type { AtmDecay } from '../../types/dashboard'
import { isMarketHours } from './atmDecayTime'

function hasTimestamp(v: AtmDecay | null | undefined): v is AtmDecay & { timestamp: string } {
    return !!v && typeof v.timestamp === 'string' && v.timestamp.length > 0
}

// Keep overlay and chart in the same session window: if latest point is out-of-session,
// fall back to the most recent in-session point from history.
export function resolveDisplayAtm(
    latest: AtmDecay | null | undefined,
    history: AtmDecay[] | null | undefined
): AtmDecay | null {
    if (hasTimestamp(latest) && isMarketHours(latest.timestamp)) {
        return latest
    }

    const hist = Array.isArray(history) ? history : []
    for (let i = hist.length - 1; i >= 0; i -= 1) {
        const row = hist[i]
        if (hasTimestamp(row) && isMarketHours(row.timestamp)) {
            return row
        }
    }

    return latest ?? null
}

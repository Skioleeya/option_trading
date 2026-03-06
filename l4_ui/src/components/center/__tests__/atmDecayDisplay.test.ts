import { describe, expect, it } from 'vitest'
import type { AtmDecay } from '../../../types/dashboard'
import { resolveDisplayAtm } from '../atmDecayDisplay'

function tick(ts: string, strike = 680): AtmDecay {
    return {
        strike,
        base_strike: strike,
        locked_at: '09:30:00',
        straddle_pct: 0.01,
        call_pct: 0.005,
        put_pct: 0.005,
        timestamp: ts,
    }
}

describe('atmDecayDisplay', () => {
    it('uses latest when latest tick is in-session', () => {
        const latest = tick('2026-03-06T10:00:00-05:00', 681)
        const out = resolveDisplayAtm(latest, [tick('2026-03-06T09:59:00-05:00', 680)])
        expect(out?.strike).toBe(681)
    })

    it('falls back to last in-session history when latest is after-hours', () => {
        const latest = tick('2026-03-06T16:10:00-05:00', 682)
        const hist = [
            tick('2026-03-06T15:58:00-05:00', 680),
            tick('2026-03-06T16:00:00-05:00', 681),
        ]
        const out = resolveDisplayAtm(latest, hist)
        expect(out?.strike).toBe(681)
    })

    it('falls back to latest when no in-session history exists', () => {
        const latest = tick('2026-03-06T16:10:00-05:00', 682)
        const out = resolveDisplayAtm(latest, [])
        expect(out?.strike).toBe(682)
    })
})

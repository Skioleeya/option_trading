import { describe, expect, it } from 'vitest'
import { resolveNavigationTarget, resolveNearestStrike } from '../depthProfileNav'

describe('depthProfileNav helpers', () => {
    it('resolves event targets from context', () => {
        const base = {
            spot: 560,
            currentSpotStrike: 560,
            callWall: 565,
            putWall: 555,
            flipLevel: 558,
        }

        expect(resolveNavigationTarget({ ...base, eventType: 'l4:nav_spot' })).toBe(560)
        expect(resolveNavigationTarget({ ...base, eventType: 'l4:nav_call_wall' })).toBe(565)
        expect(resolveNavigationTarget({ ...base, eventType: 'l4:nav_put_wall' })).toBe(555)
        expect(resolveNavigationTarget({ ...base, eventType: 'l4:nav_flip' })).toBe(558)
    })

    it('returns nearest strike when exact target is unavailable', () => {
        const strikes = [550, 555, 560, 565]
        expect(resolveNearestStrike(563, strikes)).toBe(565)
        expect(resolveNearestStrike(552, strikes)).toBe(550)
    })
})

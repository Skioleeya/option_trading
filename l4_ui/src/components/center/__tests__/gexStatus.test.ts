import { describe, expect, it } from 'vitest'
import { normalizeGexStatus, sanitizeLevelPrice } from '../gexStatus'

describe('gexStatus', () => {
    it('sanitizes invalid strike-like levels to null', () => {
        expect(sanitizeLevelPrice(null)).toBeNull()
        expect(sanitizeLevelPrice(0)).toBeNull()
        expect(sanitizeLevelPrice(-10)).toBeNull()
        expect(sanitizeLevelPrice(Number.NaN)).toBeNull()
        expect(sanitizeLevelPrice(560.25)).toBe(560.25)
    })

    it('keeps finite net_gex and sanitizes wall/flip levels', () => {
        const normalized = normalizeGexStatus({
            netGex: -1250.5,
            callWall: 0,
            flipLevel: 561.5,
            putWall: Number.POSITIVE_INFINITY,
        })
        expect(normalized.netGex).toBe(-1250.5)
        expect(normalized.callWall).toBeNull()
        expect(normalized.flipLevel).toBe(561.5)
        expect(normalized.putWall).toBeNull()
    })
})

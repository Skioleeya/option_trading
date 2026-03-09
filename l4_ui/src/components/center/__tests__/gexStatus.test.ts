import { describe, expect, it } from 'vitest'
import { ASIAN_WALL_STYLE, normalizeGexStatus, resolveAsianGexTone, sanitizeLevelPrice } from '../gexStatus'

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

    it('maps net_gex direction to asian color semantics', () => {
        expect(resolveAsianGexTone(10).direction).toBe('BULLISH')
        expect(resolveAsianGexTone(10).textClass).toContain('#ef4444')
        expect(resolveAsianGexTone(-10).direction).toBe('BEARISH')
        expect(resolveAsianGexTone(-10).textClass).toContain('#10b981')
        expect(resolveAsianGexTone(0).direction).toBe('NEUTRAL')
    })

    it('exposes asian wall style tokens', () => {
        expect(ASIAN_WALL_STYLE.call).toContain('#10b981')
        expect(ASIAN_WALL_STYLE.put).toContain('#ef4444')
    })
})

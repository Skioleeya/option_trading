import { describe, it, expect } from 'vitest'
import { getHHMM, isMarketHours, toUnixSec } from '../atmDecayTime'

describe('atmDecayTime', () => {
    it('parses HHMM from ISO timestamp', () => {
        expect(getHHMM('2026-03-06T09:30:05.984080-05:00')).toBe(930)
    })

    it('returns null for malformed timestamp', () => {
        expect(getHHMM('invalid-ts')).toBeNull()
        expect(toUnixSec('invalid-ts')).toBeNull()
    })

    it('filters to intraday range only', () => {
        expect(isMarketHours('2026-03-06T09:24:59-05:00')).toBe(false)
        expect(isMarketHours('2026-03-06T09:25:00-05:00')).toBe(true)
        expect(isMarketHours('2026-03-06T16:00:00-05:00')).toBe(true)
        expect(isMarketHours('2026-03-06T16:00:01-05:00')).toBe(false)
    })
})


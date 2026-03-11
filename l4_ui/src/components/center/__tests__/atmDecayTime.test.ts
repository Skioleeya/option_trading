import { describe, it, expect } from 'vitest'
import { getHHMM, getMarketSessionWindowUnixSec, isMarketHours, toUnixSec } from '../atmDecayTime'

describe('atmDecayTime', () => {
    it('parses HHMM in ET timezone from ISO timestamp', () => {
        expect(getHHMM('2026-03-06T09:30:05.984080-05:00')).toBe(930)
        // 14:30 UTC = 09:30 ET
        expect(getHHMM('2026-03-06T14:30:05.000000Z')).toBe(930)
    })

    it('returns null for malformed timestamp', () => {
        expect(getHHMM('invalid-ts')).toBeNull()
        expect(toUnixSec('invalid-ts')).toBeNull()
    })

    it('filters to regular session only (09:30-16:00 ET)', () => {
        expect(isMarketHours('2026-03-06T09:29:59-05:00')).toBe(false)
        expect(isMarketHours('2026-03-06T09:30:00-05:00')).toBe(true)
        expect(isMarketHours('2026-03-06T16:00:00-05:00')).toBe(true)
        expect(isMarketHours('2026-03-06T16:00:01-05:00')).toBe(false)
        // 21:00 UTC = 16:00 ET
        expect(isMarketHours('2026-03-06T20:59:59Z')).toBe(true)
        expect(isMarketHours('2026-03-06T21:00:01Z')).toBe(false)
    })

    it('derives fixed ET session window [09:30, 16:00] from any in-session timestamp', () => {
        const win = getMarketSessionWindowUnixSec('2026-03-10T15:40:24.731376-04:00')
        expect(win).not.toBeNull()
        expect(win!.from).toBe(toUnixSec('2026-03-10T09:30:00-04:00'))
        expect(win!.to).toBe(toUnixSec('2026-03-10T16:00:00-04:00'))
    })
})

import { describe, expect, it } from 'vitest'
import {
    deriveMarketStatus,
    getConnectionDotClass,
    getConnectionLabel,
    getRustIndicator,
} from '../headerState'

describe('headerState', () => {
    it('uses ET 09:30 as market open boundary', () => {
        expect(deriveMarketStatus(new Date('2026-01-06T14:29:00Z'))).toBe('CLOSE')
        expect(deriveMarketStatus(new Date('2026-01-06T14:30:00Z'))).toBe('OPEN')
    })

    it('closes at ET 16:00 and on weekend', () => {
        expect(deriveMarketStatus(new Date('2026-01-06T20:59:00Z'))).toBe('OPEN')
        expect(deriveMarketStatus(new Date('2026-01-06T21:00:00Z'))).toBe('CLOSE')
        expect(deriveMarketStatus(new Date('2026-01-10T15:00:00Z'))).toBe('CLOSE')
    })

    it('maps connection states to labels and colors', () => {
        expect(getConnectionLabel('connected')).toBe('RDS LIVE')
        expect(getConnectionLabel('stalled')).toBe('RDS STALLED')
        expect(getConnectionDotClass('connected')).toContain('#10b981')
        expect(getConnectionDotClass('stalled')).toContain('#f97316')
    })

    it('maps rust indicator states', () => {
        expect(getRustIndicator(true).label).toBe('RUST')
        expect(getRustIndicator(false).label).toBe('PY FALLBACK')
        expect(getRustIndicator(null).label).toBe('RUST ?')
    })
})

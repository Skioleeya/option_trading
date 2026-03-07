import { describe, expect, it } from 'vitest'
import { normalizeActiveOption, normalizeActiveOptions } from '../right/activeOptionsModel'

describe('activeOptionsModel', () => {
    it('normalizes CALL/PUT aliases and preserves impact/sweep fields', () => {
        const row = normalizeActiveOption({
            symbol: 'SPY',
            option_type: 'C',
            strike: '560',
            flow: '12345.6',
            impact_index: '88.1234',
            is_sweep: 1,
        })
        expect(row.option_type).toBe('CALL')
        expect(row.strike).toBe(560)
        expect(row.impact_index).toBeCloseTo(88.1234)
        expect(row.is_sweep).toBe(true)
    })

    it('adds sweep glow fallback when is_sweep=true and glow missing', () => {
        const row = normalizeActiveOption({
            option_type: 'PUT',
            is_sweep: true,
        })
        expect(row.option_type).toBe('PUT')
        expect(row.flow_glow).toContain('animate-pulse')
    })

    it('returns bounded list in input order', () => {
        const rows = normalizeActiveOptions(
            [{ strike: 1, option_type: 'C' }, { strike: 2, option_type: 'P' }],
            1
        )
        expect(rows).toHaveLength(1)
        expect(rows[0].strike).toBe(1)
    })
})


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
        expect(rows[0].slot_index).toBe(1)
    })

    it('pads to fixed 5 rows with placeholders when data is sparse', () => {
        const rows = normalizeActiveOptions(
            [{ symbol: 'SPY', strike: 560, option_type: 'C', flow: 1000 }],
            5
        )
        expect(rows).toHaveLength(5)
        expect(rows[0].is_placeholder).toBe(false)
        expect(rows[0].slot_index).toBe(1)
        expect(rows[1].is_placeholder).toBe(true)
        expect(rows[4].is_placeholder).toBe(true)
        expect(rows[4].slot_index).toBe(5)
        expect(rows[4].flow_deg_formatted).toBe('—')
    })

    it('normalizes non-array input to 5 placeholders', () => {
        const rows = normalizeActiveOptions(null, 5)
        expect(rows).toHaveLength(5)
        expect(rows.every((r) => r.is_placeholder)).toBe(true)
        expect(rows.map((r) => r.slot_index)).toEqual([1, 2, 3, 4, 5])
    })

    it('normalizes flow direction/color to asian semantics when backend value is invalid', () => {
        const row = normalizeActiveOption({
            flow: 1200,
            flow_direction: 'UNKNOWN',
            flow_color: 'text-purple-500',
            flow_intensity: 'invalid',
        })
        expect(row.flow_direction).toBe('BULLISH')
        expect(row.flow_color).toBe('text-accent-red')
        expect(row.flow_intensity).toBe('LOW')
    })

    it('forces negative flow to BEARISH green even when backend direction/color conflicts', () => {
        const row = normalizeActiveOption({
            flow: -300,
            flow_score: 1.7,
            flow_direction: 'BULLISH',
            flow_color: 'text-accent-red',
        })
        expect(row.flow_direction).toBe('BEARISH')
        expect(row.flow_color).toBe('text-accent-green')
        expect(row.flow_score).toBeCloseTo(1.7)
    })

    it('uses positive flow amount for bullish red even when flow_score is negative', () => {
        const row = normalizeActiveOption({
            flow: 1200000,
            flow_score: -2.2,
            flow_direction: 'BEARISH',
            flow_color: 'text-accent-green',
        })
        expect(row.flow_direction).toBe('BULLISH')
        expect(row.flow_color).toBe('text-accent-red')
        expect(row.flow_score).toBeCloseTo(-2.2)
    })

    it('infers flow sign from formatted value when flow is missing', () => {
        const row = normalizeActiveOption({
            flow: undefined,
            flow_deg_formatted: '-$52.7M',
        })
        expect(row.flow).toBe(-52_700_000)
        expect(row.flow_direction).toBe('BEARISH')
        expect(row.flow_color).toBe('text-accent-green')
    })

    it('preserves allowed backend flow colors and valid direction', () => {
        const row = normalizeActiveOption({
            flow: -300,
            flow_direction: 'BEARISH',
            flow_color: 'text-accent-green',
            flow_intensity: 'HIGH',
        })
        expect(row.flow_direction).toBe('BEARISH')
        expect(row.flow_color).toBe('text-accent-green')
        expect(row.flow_intensity).toBe('HIGH')
    })

    it('forces zero flow to NEUTRAL regardless of backend direction', () => {
        const row = normalizeActiveOption({
            flow: 0,
            flow_direction: 'BULLISH',
            flow_color: 'text-accent-red',
        })
        expect(row.flow_direction).toBe('NEUTRAL')
        expect(row.flow_color).toBe('text-text-secondary')
    })
})

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
            flow_direction: 'BULLISH',
            flow_color: 'text-accent-red',
        })
        expect(row.flow_direction).toBe('BEARISH')
        expect(row.flow_color).toBe('text-accent-green')
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
})

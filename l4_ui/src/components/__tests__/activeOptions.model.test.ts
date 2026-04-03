import { normalizeActiveOption, normalizeActiveOptions } from '../right/activeOptionsModel'

describe('activeOptionsModel', () => {
    const validRow = {
        symbol: 'SPY',
        option_type: 'C',
        strike: '560',
        implied_volatility: 0.2,
        volume: 1200,
        turnover: 100000,
        flow: 25000,
        flow_score: 1.2,
        impact_index: 88.1234,
        is_sweep: false,
        flow_deg_formatted: '$25K',
        flow_volume_label: '1.2K',
        flow_color: 'text-accent-red',
        flow_glow: '',
        flow_intensity: 'LOW',
        flow_direction: 'BULLISH',
    }

    it('normalizes valid backend row and preserves backend flow contract fields', () => {
        const row = normalizeActiveOption(validRow)
        expect(row.option_type).toBe('CALL')
        expect(row.strike).toBe(560)
        expect(row.flow_color).toBe('text-accent-red')
        expect(row.flow_glow).toBe('')
        expect(row.flow_direction).toBe('BULLISH')
        expect(row.flow_intensity).toBe('LOW')
    })

    it('throws when flow_direction is invalid', () => {
        expect(() =>
            normalizeActiveOption({
                ...validRow,
                flow_direction: 'UNKNOWN',
            })
        ).toThrow(/flow_direction/i)
    })

    it('throws when flow_color mismatches flow_direction', () => {
        expect(() =>
            normalizeActiveOption({
                ...validRow,
                flow_direction: 'BULLISH',
                flow_color: 'text-accent-green',
            })
        ).toThrow(/mismatch/i)
    })

    it('throws when flow sign mismatches flow_direction', () => {
        expect(() =>
            normalizeActiveOption({
                ...validRow,
                flow: -100,
                flow_direction: 'BULLISH',
                flow_color: 'text-accent-red',
            })
        ).toThrow(/negative flow/i)
    })

    it('throws when flow_glow is missing on non-placeholder rows', () => {
        expect(() =>
            normalizeActiveOption({
                ...validRow,
                flow_glow: undefined,
            })
        ).toThrow(/flow_glow/i)
    })

    it('returns bounded list sorted by VOL desc and reindexes slot', () => {
        const rows = normalizeActiveOptions(
            [
                { ...validRow, symbol: 'LOW', volume: 100 },
                { ...validRow, symbol: 'HIGH', volume: 900 },
                { ...validRow, symbol: 'MID', volume: 500 },
            ],
            2
        )
        expect(rows).toHaveLength(2)
        expect(rows[0].symbol).toBe('HIGH')
        expect(rows[1].symbol).toBe('MID')
        expect(rows[0].slot_index).toBe(1)
        expect(rows[1].slot_index).toBe(2)
    })

    it('pads to fixed 5 rows with placeholders when input is empty', () => {
        const rows = normalizeActiveOptions([], 5)
        expect(rows).toHaveLength(5)
        expect(rows.every((r) => r.is_placeholder)).toBe(true)
        expect(rows.map((r) => r.slot_index)).toEqual([1, 2, 3, 4, 5])
        expect(rows.every((r) => r.flow_signal_state === 'DEGRADED')).toBe(true)
    })
})


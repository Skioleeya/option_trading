import { describe, expect, it } from 'vitest'
import { normalizeMtfFlowState } from '../right/mtfFlowModel'

describe('mtfFlowModel', () => {
    it('returns safe defaults for null input', () => {
        const state = normalizeMtfFlowState(null)
        expect(state.consensus).toBe('NEUTRAL')
        expect(state.align_label).toBe('DIVERGE')
        expect(state.m1.strength).toBe(0)
    })

    it('normalizes malformed numeric fields to finite/clamped values', () => {
        const state = normalizeMtfFlowState({
            consensus: 'BULLISH',
            strength: '1.8',
            alignment: '-1',
            m1: { strength: 'NaN' },
        })
        expect(state.consensus).toBe('BULLISH')
        expect(state.strength).toBe(1)
        expect(state.alignment).toBe(0)
        expect(state.m1.strength).toBe(0)
    })

    it('keeps provided timeframe styling fields when valid', () => {
        const state = normalizeMtfFlowState({
            m5: {
                direction: 'BEARISH',
                regime: 'STRESS',
                regime_label: 'STR↓',
                strength: 0.75,
                dot_color: 'bg-accent-green',
                text_color: 'text-accent-green',
                shadow: 'shadow-[0_0_8px_rgba(0,214,143,0.5)]',
                border: 'border-accent-green/30',
                animate: '',
                z: -2.3,
                tier: 'MODERATE',
            },
        })
        expect(state.m5.direction).toBe('BEARISH')
        expect(state.m5.regime_label).toBe('STR↓')
        expect(state.m5.strength).toBeCloseTo(0.75)
    })
})


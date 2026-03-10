import { describe, expect, it } from 'vitest'
import { normalizeMtfFlowState, STATE_THEME } from '../right/mtfFlowModel'

describe('mtfFlowModel', () => {
    it('returns safe defaults for null input', () => {
        const state = normalizeMtfFlowState(null)
        expect(state.consensusState).toBe(0)
        expect(state.alignLabel).toBe('DIVERGE')
        expect(state.m1.kinetic_level).toBe(0)
    })

    it('normalizes malformed numeric fields to finite/clamped values', () => {
        const state = normalizeMtfFlowState({
            m1: { state: 'bad', kinetic_level: '1.8', pressure_gradient: 'NaN' },
        })
        expect(state.consensusState).toBe(0)
        expect(state.m1.state).toBe(0)
        expect(state.m1.kinetic_level).toBe(1)
        expect(state.m1.pressure_gradient).toBe(0)
    })

    it('ignores backend style tokens and uses whitelist Record mapping', () => {
        const state = normalizeMtfFlowState({
            m5: {
                state: -1,
                kinetic_level: 0.75,
                relative_displacement: -0.12,
                pressure_gradient: -0.02,
                distance_to_vacuum: 0.31,
                dot_color: 'bg-accent-green',
                text_color: 'text-accent-green',
                border: 'border-accent-green/30',
                animate: '',
            },
        })
        expect(state.m5.state).toBe(-1)
        expect(state.m5.kinetic_level).toBeCloseTo(0.75)
        expect(state.m5.tokens.dotColor).toBe(STATE_THEME[-1].dotColor)
        expect(state.m5.tokens.textColor).toBe(STATE_THEME[-1].textColor)
        expect(state.m5.tokens.borderColor).toBe(STATE_THEME[-1].borderColor)
    })
})

import { describe, expect, it } from 'vitest'
import { normalizeSkewDynamicsState } from '../right/skewDynamicsModel'

describe('skewDynamicsModel', () => {
    it('returns zero state when input is null', () => {
        const skew = normalizeSkewDynamicsState(null)
        expect(skew.value).toBe('—')
        expect(skew.state_label).toBe('NEUTRAL')
        expect(skew.badge).toBe('badge-neutral')
    })

    it('fills missing fields with defaults', () => {
        const skew = normalizeSkewDynamicsState({
            value: '-0.22',
            state_label: 'SPECULATIVE',
            color_class: 'text-accent-red',
        })
        expect(skew.value).toBe('-0.22')
        expect(skew.state_label).toBe('SPECULATIVE')
        expect(skew.color_class).toBe('text-accent-red')
        expect(skew.bg_class).toBe('bg-bg-card')
    })
})

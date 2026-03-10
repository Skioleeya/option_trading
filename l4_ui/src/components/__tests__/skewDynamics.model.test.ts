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
        expect(skew.bg_class).toBe('bg-accent-red/5')
    })

    it('preserves unavailable rendering tokens', () => {
        const skew = normalizeSkewDynamicsState({
            value: 'N/A',
            state_label: 'UNAVAILABLE',
            color_class: 'text-text-secondary',
            border_class: 'border-bg-border',
            bg_class: 'bg-bg-card',
            shadow_class: 'shadow-none',
            badge: 'badge-neutral',
        })
        expect(skew.value).toBe('N/A')
        expect(skew.state_label).toBe('UNAVAILABLE')
        expect(skew.badge).toBe('badge-neutral')
    })
})

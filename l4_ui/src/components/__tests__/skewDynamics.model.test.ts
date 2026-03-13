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

    it('keeps contract stable for canonical rr25-driven values', () => {
        const skew = normalizeSkewDynamicsState({
            value: '-0.07',
            state_label: 'SPECULATIVE',
        })
        expect(skew.value).toBe('-0.07')
        expect(skew.state_label).toBe('SPECULATIVE')
        expect(skew.badge).toBe('badge-red')
    })

    it('hard-cuts unknown state labels to NEUTRAL and ignores backend color tokens', () => {
        const skew = normalizeSkewDynamicsState({
            value: '-0.31',
            state_label: 'CUSTOM_STATE',
            color_class: 'text-accent-green',
            border_class: 'border-accent-green/40',
            bg_class: 'bg-accent-green/5',
            shadow_class: 'shadow-custom-backend',
            badge: 'badge-green',
        })

        expect(skew.state_label).toBe('NEUTRAL')
        expect(skew.color_class).toBe('text-text-primary')
        expect(skew.badge).toBe('badge-neutral')
    })

    it('formats numeric skew value to fixed precision in non-unavailable states', () => {
        const skew = normalizeSkewDynamicsState({
            value: -0.3333,
            state_label: 'SPECULATIVE',
        })

        expect(skew.value).toBe('-0.33')
    })
})


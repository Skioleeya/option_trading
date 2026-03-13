import { normalizeTacticalTriadState } from '../right/tacticalTriadModel'

describe('tacticalTriadModel', () => {
    it('returns full zero state when input is null', () => {
        const triad = normalizeTacticalTriadState(null)
        expect(triad.vrp.value).toBe('—')
        expect(triad.charm.state_label).toBe('STABLE')
        expect(triad.svol.state_label).toBe('S-VOL')
    })

    it('fills missing cards with safe defaults', () => {
        const triad = normalizeTacticalTriadState({
            vrp: { value: '+1.2%', state_label: 'FAIR' },
        })

        expect(triad.vrp.value).toBe('+1.2%')
        expect(triad.vrp.state_label).toBe('FAIR')
        expect(triad.charm.value).toBe('—')
        expect(triad.svol.value).toBe('—')
    })

    it('keeps charm contract stable for canonical raw-sum source values', () => {
        const triad = normalizeTacticalTriadState({
            charm: {
                value: '-7.7',
                state_label: 'DECAYING',
                sub_label: 'ACCELERATING',
                sub_intensity: 'HIGH',
            },
        })

        expect(triad.charm.value).toBe('-7.7')
        expect(triad.charm.state_label).toBe('DECAYING')
        expect(triad.charm.sub_label).toBe('ACCELERATING')
    })

    it('keeps MEDIUM intensity and hard-cuts MODERATE compatibility', () => {
        const medium = normalizeTacticalTriadState({
            vrp: { value: '+2.6%', state_label: 'BUY', sub_intensity: 'MEDIUM', sub_label: 'BREAKOUT' },
        })
        const moderate = normalizeTacticalTriadState({
            vrp: { value: '+2.6%', state_label: 'BUY', sub_intensity: 'MODERATE', sub_label: 'BREAKOUT' },
        })

        expect(medium.vrp.sub_intensity).toBe('MEDIUM')
        expect(medium.vrp.animation).toBe('')
        expect(moderate.vrp.sub_intensity).toBe('LOW')
    })

    it('maps VRP BUY/SELL and SVOL TOXIC/FLIP to strict tones', () => {
        const triad = normalizeTacticalTriadState({
            vrp: { value: '+1.2%', state_label: 'BUY', sub_label: 'BREAKOUT', sub_intensity: 'LOW' },
            charm: { value: '0.0', state_label: 'STABLE', sub_label: 'STABLE', sub_intensity: 'LOW' },
            svol: { value: '0.31', state_label: 'FLIP', sub_label: 'FLIP RISK', sub_intensity: 'HIGH' },
        })
        const triadSell = normalizeTacticalTriadState({
            vrp: { value: '-1.2%', state_label: 'SELL', sub_label: 'WASH OUT', sub_intensity: 'LOW' },
            charm: { value: '0.0', state_label: 'STABLE', sub_label: 'STABLE', sub_intensity: 'LOW' },
            svol: { value: '0.31', state_label: 'TOXIC', sub_label: 'TOXIC DRAG', sub_intensity: 'LOW' },
        })

        expect(triad.vrp.color_class).toBe('text-accent-red')
        expect(triad.vrp.border_class).toBe('border-accent-red/40')
        expect(triad.svol.color_class).toBe('text-accent-amber')
        expect(triad.svol.border_class).toBe('border-accent-amber/40')
        expect(triad.svol.animation).toBe('animate-pulse')

        expect(triadSell.vrp.color_class).toBe('text-accent-green')
        expect(triadSell.vrp.border_class).toBe('border-accent-green/40')
        expect(triadSell.svol.color_class).toBe('text-accent-red')
        expect(triadSell.svol.border_class).toBe('border-accent-red/40')
    })

    it('ignores backend class tokens and enforces local semantic map', () => {
        const triad = normalizeTacticalTriadState({
            vrp: {
                value: '+0.8%',
                state_label: 'BUY',
                sub_label: 'BREAKOUT',
                sub_intensity: 'LOW',
                color_class: 'text-accent-green',
                border_class: 'border-accent-green/40',
                bg_class: 'bg-accent-green/5',
                shadow_class: 'shadow-custom-backend',
            },
        })

        expect(triad.vrp.color_class).toBe('text-accent-red')
        expect(triad.vrp.border_class).toBe('border-accent-red/40')
        expect(triad.vrp.bg_class).toBe('bg-accent-red/5')
    })

    it('infers svol state from sub-label when backend sends placeholder state', () => {
        const triad = normalizeTacticalTriadState({
            svol: {
                value: '0.31',
                state_label: 'S-VOL',
                sub_label: 'MOMENTUM',
                sub_intensity: 'LOW',
            },
        })

        expect(triad.svol.state_label).toBe('GRIND')
        expect(triad.svol.color_class).toBe('text-accent-cyan')
    })

    it('uses STBL as svol state when value exists but state/sub-state are placeholders', () => {
        const triad = normalizeTacticalTriadState({
            svol: {
                value: '0.08',
                state_label: 'S-VOL',
                sub_label: 'NEUTRAL',
                sub_intensity: 'LOW',
            },
        })

        expect(triad.svol.state_label).toBe('STBL')
    })
})


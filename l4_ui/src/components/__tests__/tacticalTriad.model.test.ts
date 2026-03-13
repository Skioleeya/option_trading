import { describe, expect, it } from 'vitest'
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
})

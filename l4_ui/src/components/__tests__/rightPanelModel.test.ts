import { describe, expect, it } from 'vitest'
import type { DashboardPayload } from '../../types/dashboard'
import { deriveRightPanelContracts } from '../right/rightPanelModel'

describe('rightPanelModel', () => {
    it('derives typed right-panel contracts from payload ui_state', () => {
        const payload = {
            type: 'dashboard_update',
            timestamp: '2026-03-11T14:20:00Z',
            spot: 560.1,
            agent_g: {
                agent: 'agent_g',
                signal: 'NEUTRAL',
                as_of: '2026-03-11T14:20:00Z',
                data: {
                    fused_signal: {
                        direction: 'BULLISH',
                        confidence: 0.8,
                        weights: {},
                        regime: 'NORMAL',
                        iv_regime: 'NORMAL',
                        gex_intensity: 'HIGH',
                        explanation: 'ignore',
                        components: {},
                    },
                    ui_state: {
                        micro_stats: {
                            net_gex: { label: 'GEX +88M', badge: 'badge-red' },
                            wall_dyn: { label: 'RETREAT', badge: 'badge-red' },
                            vanna: { label: 'NORMAL', badge: 'badge-neutral' },
                            momentum: { label: 'BULLISH', badge: 'badge-red' },
                        },
                        wall_migration: [],
                        depth_profile: [],
                        macro_volume_map: {},
                        atm: null,
                        tactical_triad: null,
                        skew_dynamics: null,
                        mtf_flow: null,
                        active_options: [{ symbol: 'SPY', option_type: 'CALL', strike: 560, implied_volatility: 0.2, volume: 1, turnover: 1, flow: 1 }],
                    },
                },
            },
        } as unknown as DashboardPayload

        const out = deriveRightPanelContracts(payload)

        expect(out.fused?.direction).toBe('BULLISH')
        expect(out.netGex?.label).toBe('GEX +88M')
        expect(out.activeOptions?.length).toBe(1)
    })

    it('returns null-safe defaults when payload is empty', () => {
        const out = deriveRightPanelContracts(null)
        expect(out.fused).toBeNull()
        expect(out.netGex).toBeNull()
        expect(out.tacticalTriad).toBeNull()
        expect(out.skewDynamics).toBeNull()
        expect(out.mtfFlow).toBeNull()
        expect(out.activeOptions).toBeNull()
    })
})

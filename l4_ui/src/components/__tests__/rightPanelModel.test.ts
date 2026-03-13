import type { DashboardPayload } from '../../types/dashboard'
import {
    deriveRightPanelContracts,
    RIGHT_PANEL_ACTIVE_OPTION_ROWS,
} from '../right/rightPanelModel'

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
        expect(out.activeOptions).toHaveLength(RIGHT_PANEL_ACTIVE_OPTION_ROWS)
        expect(out.activeOptions[0].symbol).toBe('SPY')
        expect(out.activeOptions[0].slot_index).toBe(1)
        expect(out.activeOptions[1].is_placeholder).toBe(true)
    })

    it('returns normalized defaults when payload is empty', () => {
        const out = deriveRightPanelContracts(null)

        expect(out.fused).toBeNull()
        expect(out.netGex).toBeNull()
        expect(out.tacticalTriad.vrp.state_label).toBe('VRP')
        expect(out.skewDynamics.state_label).toBe('NEUTRAL')
        expect(out.mtfFlow.alignLabel).toBe('DIVERGE')
        expect(out.activeOptions).toHaveLength(RIGHT_PANEL_ACTIVE_OPTION_ROWS)
        expect(out.activeOptions.every((row) => row.is_placeholder === true)).toBe(true)
    })

    it('sanitizes dirty style/state payloads at bus level', () => {
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
                        direction: 'NEUTRAL',
                        confidence: 0.5,
                        weights: {},
                        regime: 'NORMAL',
                        iv_regime: 'NORMAL',
                        gex_intensity: 'LOW',
                        explanation: 'ignore',
                        components: {},
                    },
                    ui_state: {
                        micro_stats: {
                            net_gex: { label: 'GEX +20M', badge: 'badge-injected' },
                            wall_dyn: { label: 'RETREAT', badge: 'badge-red' },
                            vanna: { label: 'NORMAL', badge: 'badge-neutral' },
                            momentum: { label: 'BULLISH', badge: 'badge-red' },
                        },
                        wall_migration: [],
                        depth_profile: [],
                        macro_volume_map: {},
                        atm: null,
                        tactical_triad: {
                            vrp: {
                                value: '1.2%',
                                state_label: 'BULL',
                                color_class: 'text-accent-green',
                                border_class: 'border-accent-green/40',
                                bg_class: 'bg-accent-green/5',
                                shadow_class: 'shadow-none',
                                animation: '',
                                sub_intensity: 'HIGH',
                                sub_label: 'BREAKOUT',
                            },
                            charm: {
                                value: '0.1',
                                state_label: 'NEUTRAL',
                                color_class: 'text-accent-red',
                                border_class: 'border-accent-red/40',
                                bg_class: 'bg-accent-red/5',
                                shadow_class: 'shadow-none',
                                multiplier: null,
                                sub_intensity: 'MEDIUM',
                                sub_label: 'NEUTRAL',
                            },
                            svol: {
                                value: '0.4',
                                state_label: 'S-VOL',
                                color_class: 'text-accent-red',
                                border_class: 'border-accent-red/40',
                                bg_class: 'bg-accent-red/5',
                                shadow_class: 'shadow-none',
                                animation: '',
                                sub_intensity: 'HIGH',
                                sub_label: 'MOMENTUM',
                            },
                        },
                        skew_dynamics: {
                            value: '-0.2',
                            state_label: 'DEFENSIVE',
                            color_class: 'text-accent-red',
                            border_class: 'border-accent-red/40',
                            bg_class: 'bg-accent-red/5',
                            shadow_class: 'shadow-none',
                            badge: 'badge-red',
                        },
                        mtf_flow: {
                            m1: { state: 1, relative_displacement: 0.1, pressure_gradient: 0.1, distance_to_vacuum: 0.1, kinetic_level: 0.9 },
                            m5: { state: -1, relative_displacement: 0.1, pressure_gradient: 0.1, distance_to_vacuum: 0.1, kinetic_level: 0.9 },
                            m15: { state: 0, relative_displacement: 0.1, pressure_gradient: 0.1, distance_to_vacuum: 0.1, kinetic_level: 0.9 },
                        },
                        active_options: [
                            {
                                symbol: 'SPY',
                                option_type: 'CALL',
                                strike: 560,
                                implied_volatility: 0.2,
                                volume: 100,
                                turnover: 1000,
                                flow: 100000,
                                flow_color: 'text-accent-green',
                                flow_intensity: 'HIGH',
                            },
                        ],
                    },
                },
            },
        } as unknown as DashboardPayload

        const out = deriveRightPanelContracts(payload)

        expect(out.netGex?.badge).toBe('badge-neutral')
        expect(out.tacticalTriad.vrp.color_class).toBe('text-accent-red')
        expect(out.tacticalTriad.svol.state_label).toBe('GRIND')
        expect(out.skewDynamics.badge).toBe('badge-green')
        expect(out.activeOptions[0].flow_color).toBe('text-accent-red')
    })
})


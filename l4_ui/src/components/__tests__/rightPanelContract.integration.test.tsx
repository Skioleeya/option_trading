import { cleanup, render, screen } from '@testing-library/react'
import { useDashboardStore } from '../../store/dashboardStore'
import type {
    ActiveOption,
    DashboardPayload,
    MtfFlowState,
    SkewDynamicsState,
    TacticalTriadState,
} from '../../types/dashboard'
import { ActiveOptions } from '../right/ActiveOptions'
import { MtfFlow } from '../right/MtfFlow'
import { SkewDynamics } from '../right/SkewDynamics'
import { TacticalTriad } from '../right/TacticalTriad'

function makePayload(
    tacticalTriad: TacticalTriadState,
    skewDynamics: SkewDynamicsState,
    mtfFlow: MtfFlowState,
    activeOptions: ActiveOption[]
): DashboardPayload {
    return {
        type: 'dashboard_update',
        timestamp: '2026-03-07T13:30:00Z',
        spot: 560.5,
        agent_g: {
            agent: 'agent_g',
            signal: 'BULLISH',
            as_of: '2026-03-07T13:30:00Z',
            data: {
                agent_a: {
                    signal: 'BULLISH',
                    data: { spot: 560.5, vwap: 560.0, vwap_std: 0.5, slope: 0.2 },
                },
                agent_b: {
                    signal: 'BULLISH',
                    data: {
                        net_gex: 120.5,
                        spy_atm_iv: 0.185,
                        gamma_walls: { call_wall: 565.0, put_wall: 555.0 },
                        gamma_flip: false,
                        gamma_flip_level: 558.0,
                        per_strike_gex: [],
                        micro_structure: null,
                        iv_confidence: 0.9,
                        wall_confidence: 0.8,
                        vanna_confidence: 0.7,
                        mtf_consensus: { timeframes: {} },
                    },
                },
                net_gex: 120.5,
                gex_regime: 'DAMPING',
                gamma_walls: { call_wall: 565.0, put_wall: 555.0 },
                gamma_flip_level: 558.0,
                spy_atm_iv: 0.185,
                trap_state: 'NONE',
                fused_signal: {
                    direction: 'BULLISH',
                    confidence: 0.82,
                    weights: { iv: 0.3 },
                    regime: 'NORMAL',
                    iv_regime: 'NORMAL',
                    gex_intensity: 'HIGH',
                    explanation: 'contract-test',
                    components: {},
                },
                micro_structure: null,
                ui_state: {
                    micro_stats: {
                        net_gex: { label: 'GEX +120M', badge: 'badge-red' },
                        wall_dyn: { label: 'DAMPING', badge: 'badge-neutral' },
                        vanna: { label: 'GRIND_STABLE', badge: 'badge-neutral' },
                        momentum: { label: 'BULLISH', badge: 'badge-red' },
                    },
                    wall_migration: [],
                    depth_profile: [],
                    macro_volume_map: {},
                    atm: null,
                    tactical_triad: tacticalTriad,
                    skew_dynamics: skewDynamics,
                    mtf_flow: mtfFlow,
                    active_options: activeOptions,
                },
            },
        },
    }
}

afterEach(() => {
    cleanup()
    useDashboardStore.setState({ payload: null })
})

describe('Right panel typed contract integration', () => {
    it('consumes typed payload contracts from store and renders expected values', () => {
        const tacticalTriad: TacticalTriadState = {
            vrp: {
                value: '+1.2%',
                state_label: 'FAIR',
                color_class: 'text-text-primary',
                border_class: 'border-bg-border',
                bg_class: 'bg-bg-card',
                shadow_class: 'shadow-none',
                animation: '',
                sub_intensity: 'LOW',
                sub_label: 'NEUTRAL',
            },
            charm: {
                value: '2.4',
                state_label: 'RISING',
                color_class: 'text-accent-red',
                border_class: 'border-accent-red/40',
                bg_class: 'bg-accent-red/5',
                shadow_class: 'shadow-none',
                multiplier: null,
                sub_intensity: 'LOW',
                sub_label: 'REVERSAL',
            },
            svol: {
                value: '0.31',
                state_label: 'GRIND',
                color_class: 'text-accent-cyan',
                border_class: 'border-accent-cyan/40',
                bg_class: 'bg-accent-cyan/5',
                shadow_class: 'shadow-none',
                animation: '',
                sub_intensity: 'LOW',
                sub_label: 'MOMENTUM',
            },
        }
        const skewDynamics: SkewDynamicsState = {
            value: '-0.33',
            state_label: 'SPECULATIVE',
            color_class: 'text-accent-red',
            border_class: 'border-accent-red/40',
            bg_class: 'bg-accent-red/5',
            shadow_class: 'shadow-none',
            badge: 'badge-red',
        }
        const mtfFlow: MtfFlowState = {
            m1: {
                state: 1,
                relative_displacement: 0.02,
                pressure_gradient: 0.001,
                distance_to_vacuum: 0.3,
                kinetic_level: 0.8,
            },
            m5: {
                state: 1,
                relative_displacement: 0.012,
                pressure_gradient: 0.0004,
                distance_to_vacuum: 0.5,
                kinetic_level: 0.7,
            },
            m15: {
                state: 0,
                relative_displacement: 0,
                pressure_gradient: 0,
                distance_to_vacuum: 0.7,
                kinetic_level: 0.2,
            },
        }
        const activeOptions: ActiveOption[] = [
            {
                symbol: 'SPY',
                option_type: 'CALL',
                strike: 560,
                implied_volatility: 0.22,
                volume: 50000,
                turnover: 10000000,
                flow: 1250000,
                flow_score: -0.9,
                impact_index: 88.1234,
                is_sweep: true,
                flow_deg_formatted: '$1.25M',
                flow_volume_label: '50K',
                flow_color: 'text-accent-red',
                flow_glow: '',
                flow_intensity: 'HIGH',
                flow_direction: 'BULLISH',
            },
        ]

        useDashboardStore.setState({
            payload: makePayload(tacticalTriad, skewDynamics, mtfFlow, activeOptions),
        })

        render(
            <>
                <TacticalTriad />
                <SkewDynamics />
                <MtfFlow />
                <ActiveOptions />
            </>
        )

        expect(screen.getByText('FAIR')).toBeInTheDocument()
        expect(screen.getByText('SPECULATIVE')).toBeInTheDocument()
        expect(screen.getByText('2.4')).toBeInTheDocument()
        expect(screen.getByText('SPLIT')).toBeInTheDocument()
        expect(screen.getByText('88.12')).toBeInTheDocument()
        expect(screen.getByText('$1.25M')).toBeInTheDocument()
        expect(screen.getByText('50K')).toBeInTheDocument()
    })

    it('renders unavailable skew as N/A with neutral styling contract', () => {
        const tacticalTriad: TacticalTriadState = {
            vrp: {
                value: '0.0%',
                state_label: 'FAIR',
                color_class: 'text-text-primary',
                border_class: 'border-bg-border',
                bg_class: 'bg-bg-card',
                shadow_class: 'shadow-none',
                animation: '',
                sub_intensity: 'LOW',
                sub_label: 'NEUTRAL',
            },
            charm: {
                value: '0.0',
                state_label: 'NEUTRAL',
                color_class: 'text-text-primary',
                border_class: 'border-bg-border',
                bg_class: 'bg-bg-card',
                shadow_class: 'shadow-none',
                multiplier: null,
                sub_intensity: 'LOW',
                sub_label: 'NEUTRAL',
            },
            svol: {
                value: '0.0',
                state_label: 'UNAVAILABLE',
                color_class: 'text-text-secondary',
                border_class: 'border-bg-border',
                bg_class: 'bg-bg-card',
                shadow_class: 'shadow-none',
                animation: '',
                sub_intensity: 'LOW',
                sub_label: 'MOMENTUM',
            },
        }
        const skewDynamics: SkewDynamicsState = {
            value: 'N/A',
            state_label: 'UNAVAILABLE',
            color_class: 'text-text-secondary',
            border_class: 'border-bg-border',
            bg_class: 'bg-bg-card',
            shadow_class: 'shadow-none',
            badge: 'badge-neutral',
        }
        const mtfFlow: MtfFlowState = {
            m1: {
                state: 0,
                relative_displacement: 0.0,
                pressure_gradient: 0.0,
                distance_to_vacuum: 0.0,
                kinetic_level: 0.1,
            },
            m5: {
                state: 0,
                relative_displacement: 0.0,
                pressure_gradient: 0.0,
                distance_to_vacuum: 0.0,
                kinetic_level: 0.1,
            },
            m15: {
                state: 0,
                relative_displacement: 0.0,
                pressure_gradient: 0.0,
                distance_to_vacuum: 0.0,
                kinetic_level: 0.1,
            },
        }

        useDashboardStore.setState({
            payload: makePayload(tacticalTriad, skewDynamics, mtfFlow, []),
        })

        render(<SkewDynamics />)

        expect(screen.getByText('UNAVAILABLE')).toBeInTheDocument()
        expect(screen.getByText('N/A')).toBeInTheDocument()
    })

    it('renders active options as fixed 5 rows when payload has fewer rows', () => {
        const sparseOptions: ActiveOption[] = [
            {
                symbol: 'SPY',
                option_type: 'CALL',
                strike: 560,
                implied_volatility: 0.2,
                volume: 22000,
                turnover: 1500000,
                flow: 520000,
                impact_index: 88.12,
            },
            {
                symbol: 'SPY',
                option_type: 'PUT',
                strike: 559,
                implied_volatility: 0.21,
                volume: 18000,
                turnover: 1200000,
                flow: -410000,
                impact_index: 77.11,
            },
            {
                symbol: 'SPY',
                option_type: 'CALL',
                strike: 561,
                implied_volatility: 0.19,
                volume: 17000,
                turnover: 980000,
                flow: 210000,
                impact_index: 54.0,
            },
        ]

        render(<ActiveOptions options={sparseOptions} />)

        // 1 header row + 5 data rows
        expect(screen.getAllByRole('row')).toHaveLength(6)
        expect(screen.getByText('5')).toBeInTheDocument()
        expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    })
})



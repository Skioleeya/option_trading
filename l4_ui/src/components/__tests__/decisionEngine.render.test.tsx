import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import type { FusedSignal } from '../../types/dashboard'
import { DecisionEngine } from '../right/DecisionEngine'
import { useDashboardStore } from '../../store/dashboardStore'

function makeFused(partial?: Partial<FusedSignal>): FusedSignal {
    return {
        direction: 'NEUTRAL',
        confidence: 0,
        weights: {},
        regime: 'NORMAL',
        iv_regime: 'NORMAL',
        gex_intensity: 'NEUTRAL',
        explanation: '',
        components: {},
        ...partial,
    }
}

afterEach(() => {
    cleanup()
    useDashboardStore.setState({
        payload: null,
    } as any)
})

describe('DecisionEngine component render', () => {
    it('uses micro stats net_gex badge as gex source of truth when present', () => {
        const fromStore = makeFused({
            direction: 'BULLISH',
            confidence: 0.91,
            gex_intensity: 'STRONG_POSITIVE',
            explanation: 'store explanation',
        })
        const fromProp = makeFused({
            direction: 'BEARISH',
            confidence: 0.12,
            explanation: 'prop explanation',
        })

        useDashboardStore.setState({
            payload: {
                type: 'dashboard_update',
                timestamp: '2026-03-06T19:18:00Z',
                spot: 560,
                agent_g: {
                    agent: 'agent_g',
                    signal: 'NEUTRAL',
                    as_of: '2026-03-06T19:18:00Z',
                    data: {
                        fused_signal: fromStore,
                        ui_state: {
                            micro_stats: {
                                net_gex: { label: 'VOLATILE', badge: 'badge-hollow-purple' },
                            },
                        },
                    },
                },
            },
        } as any)

        render(<DecisionEngine fused={fromProp} />)

        expect(screen.getByText('BULLISH')).toBeInTheDocument()
        expect(screen.getByText('91%')).toBeInTheDocument()
        const gex = screen.getByText('GEX VOLATILE')
        expect(gex).toBeInTheDocument()
        expect(gex).toHaveClass('badge-hollow-purple')
        expect(screen.queryByText('store explanation')).not.toBeInTheDocument()
        expect(screen.queryByText('prop explanation')).not.toBeInTheDocument()
    })

    it('falls back to fused gex_intensity when micro stats net_gex is missing', () => {
        const fromProp = makeFused({
            direction: 'HALT',
            confidence: 0.33,
            regime: 'HIGH_VOL',
            gex_intensity: 'EXTREME_NEGATIVE',
            explanation: 'prop explanation',
        })

        render(<DecisionEngine fused={fromProp} />)

        expect(screen.getByText('HALT')).toBeInTheDocument()
        expect(screen.getByText('33%')).toBeInTheDocument()
        expect(screen.getByText('HIGH VOL')).toBeInTheDocument()
        expect(screen.getByText('GEX EXTREME NEGATIVE')).toBeInTheDocument()
        expect(screen.getByText('GEX EXTREME NEGATIVE')).toHaveClass('badge-hollow-purple')
        expect(screen.queryByText('prop explanation')).not.toBeInTheDocument()
    })

    it('does not duplicate GEX prefix when micro stats label already includes it', () => {
        const fromStore = makeFused({
            direction: 'NEUTRAL',
            confidence: 0.45,
            gex_intensity: 'NEUTRAL',
        })

        useDashboardStore.setState({
            payload: {
                type: 'dashboard_update',
                timestamp: '2026-03-06T19:18:00Z',
                spot: 560,
                agent_g: {
                    agent: 'agent_g',
                    signal: 'NEUTRAL',
                    as_of: '2026-03-06T19:18:00Z',
                    data: {
                        fused_signal: fromStore,
                        ui_state: {
                            micro_stats: {
                                net_gex: { label: 'GEX DAMPING', badge: 'badge-hollow-green' },
                            },
                        },
                    },
                },
            },
        } as any)

        render(<DecisionEngine />)

        expect(screen.getByText('GEX DAMPING')).toBeInTheDocument()
        expect(screen.queryByText('GEX GEX DAMPING')).not.toBeInTheDocument()
    })
})

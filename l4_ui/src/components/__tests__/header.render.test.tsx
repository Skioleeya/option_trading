import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { Header } from '../center/Header'
import { useDashboardStore } from '../../store/dashboardStore'

afterEach(() => {
    cleanup()
    useDashboardStore.setState({
        payload: null,
        connectionStatus: 'connecting',
        spot: null,
        ivPct: null,
    } as any)
})

describe('Header component render', () => {
    it('renders ET timestamp and status indicators from store payload', () => {
        useDashboardStore.setState({
            connectionStatus: 'connected',
            spot: 512.34,
            ivPct: 0.245,
            payload: {
                type: 'dashboard_update',
                timestamp: '2026-03-06T15:30:45Z',
                spot: 512.34,
                rust_active: true,
                agent_g: {
                    agent: 'agent_g',
                    signal: 'NEUTRAL',
                    as_of: '2026-03-06T15:30:45Z',
                    data: {
                        fused_signal: {
                            direction: 'NEUTRAL',
                            confidence: 0.2,
                            weights: {},
                            regime: 'NORMAL',
                            iv_regime: 'ELEVATED',
                            gex_intensity: 'NEUTRAL',
                            explanation: '',
                            components: {},
                        },
                        ui_state: {
                            iv_velocity: {
                                state: 'VOL_EXPANSION',
                                confidence: 0.8,
                                iv_roc: 0.12,
                                spot_roc: 0.01,
                            },
                        },
                    },
                },
            },
        } as any)

        render(<Header marketStatus="OPEN" />)

        expect(screen.getByText('10:30:45 ET')).toBeInTheDocument()
        expect(screen.getByText('RDS LIVE')).toBeInTheDocument()
        expect(screen.getByText('RUST')).toBeInTheDocument()
        expect(screen.getByText(/VOL_EXPANSION/)).toBeInTheDocument()
        expect(screen.getByText('24.50%')).toBeInTheDocument()
    })

    it('uses prop timestamp fallback when payload timestamp is missing', () => {
        render(
            <Header
                marketStatus="CLOSE"
                as_of="2026-03-06T18:00:00Z"
                spot={520.1}
                ivPct={0.1}
            />
        )

        expect(screen.getByText('13:00:00 ET')).toBeInTheDocument()
        expect(screen.getByText('10.00%')).toBeInTheDocument()
    })
})

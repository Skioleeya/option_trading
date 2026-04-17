import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Header } from '../center/Header'
import { useDashboardStore } from '../../store/dashboardStore'

afterEach(() => {
    cleanup()
    vi.useRealTimers()
    useDashboardStore.setState({
        payload: null,
        connectionStatus: 'connecting',
        spot: null,
        ivPct: null,
        headerVolatility: null,
    } as any)
})

describe('Header component render', () => {
    it('renders ET timestamp and status indicators from store payload', () => {
        useDashboardStore.setState({
            connectionStatus: 'connected',
            spot: 512.34,
            ivPct: 0.245,
            headerVolatility: {
                lookback_days: 20,
                lookback_effective_days: 12,
                ivr: 72,
                ivp: 68,
                term_structure: {
                    primary: { anchor: '1DTE', symbol: 'SPY.US', ratio: 1.12, state: 'INVERTED' },
                    secondary: { anchor: '.VIX.US', symbol: '.VIX.US', ratio: 1.08, state: 'INVERTED' },
                },
                iv_price_relation: {
                    window_seconds: 120,
                    iv_change_pp: 2.2,
                    price_change_pct: -0.3,
                    beta_pp_per_pct: 7.3,
                    state: 'INVERSE_CONFIRM',
                },
            },
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
                        header_volatility: {
                            lookback_days: 20,
                            lookback_effective_days: 12,
                            ivr: 72,
                            ivp: 68,
                            term_structure: {
                                primary: { anchor: '1DTE', symbol: 'SPY.US', ratio: 1.12, state: 'INVERTED' },
                                secondary: { anchor: '.VIX.US', symbol: '.VIX.US', ratio: 1.08, state: 'INVERTED' },
                            },
                            iv_price_relation: {
                                window_seconds: 120,
                                iv_change_pp: 2.2,
                                price_change_pct: -0.3,
                                beta_pp_per_pct: 7.3,
                                state: 'INVERSE_CONFIRM',
                            },
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

        expect(screen.getByTestId('header-center').className).toContain('l4-header__center')
        expect(screen.getByTestId('header-center-shell').className).toContain('l4-header__center-shell')
        expect(screen.getByTestId('header-group-left').className).toContain('l4-header__group-left')
        expect(screen.getByTestId('header-group-middle').className).toContain('l4-header__group-middle')
        expect(screen.getByTestId('header-group-right').className).toContain('l4-header__group-right')
        const ivSummary = screen.getByTestId('header-iv-summary')
        const middleGroup = screen.getByTestId('header-group-middle')
        const detailBadgeWrap = screen.getByTestId('header-detail-badge-wrap')
        const volMicro = screen.getByTestId('header-vol-micro')
        expect(ivSummary).toBeInTheDocument()
        expect(middleGroup.contains(ivSummary)).toBe(true)
        expect(detailBadgeWrap.contains(ivSummary)).toBe(false)
        expect(screen.getByTestId('header-vol-badge')).toBeInTheDocument()
        expect(volMicro).toBeInTheDocument()
        expect(screen.queryByText('...')).not.toBeInTheDocument()
        expect(screen.getByText('10:30:45 ET')).toBeInTheDocument()
        expect(screen.getByText('RDS LIVE')).toBeInTheDocument()
        expect(screen.getByText('RUST')).toBeInTheDocument()
        expect(screen.getByText('TACTICAL OFFENSIVE')).toBeInTheDocument()
        expect(screen.queryByText(/SCALE/)).not.toBeInTheDocument()
        expect(screen.getByText('IV')).toBeInTheDocument()
        expect(screen.getByText(/UP VOL_EXPANSION/)).toBeInTheDocument()
        expect(screen.getByText('24.50%')).toBeInTheDocument()
        expect(volMicro.textContent).toContain('R72')
        expect(volMicro.textContent).toContain('P68')
        expect(volMicro.textContent).toContain('1D 1.12')
        expect(volMicro.textContent).toContain('VX 1.08')
        expect(volMicro.textContent).toContain('β INV')
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
        expect(screen.queryByText(/SCALE/)).not.toBeInTheDocument()
        expect(screen.getByTestId('header-group-left').className).toContain('l4-header__group-left')
        expect(screen.getByTestId('header-group-right')).toBeInTheDocument()
    })

    it('applies broker-style SPY tick direction classes for up and down ticks', () => {
        vi.useFakeTimers()

        const { rerender } = render(<Header marketStatus="OPEN" spot={710.14} />)
        const spotValue = screen.getByTestId('header-spot-value')

        expect(spotValue.className).toContain('l4-header__spot-value--neutral')
        expect(spotValue.className).not.toContain('l4-header__spot-value--tick-up')
        expect(spotValue.className).not.toContain('l4-header__spot-value--tick-down')

        act(() => {
            rerender(<Header marketStatus="OPEN" spot={710.24} />)
        })

        expect(spotValue.className).toContain('l4-header__spot-value--up')
        expect(spotValue.className).toContain('l4-header__spot-value--tick-up')

        act(() => {
            vi.advanceTimersByTime(400)
        })

        expect(spotValue.className).toContain('l4-header__spot-value--up')
        expect(spotValue.className).not.toContain('l4-header__spot-value--tick-up')

        act(() => {
            rerender(<Header marketStatus="OPEN" spot={710.08} />)
        })

        expect(spotValue.className).toContain('l4-header__spot-value--down')
        expect(spotValue.className).toContain('l4-header__spot-value--tick-down')

        act(() => {
            vi.advanceTimersByTime(400)
        })

        expect(spotValue.className).toContain('l4-header__spot-value--down')
        expect(spotValue.className).not.toContain('l4-header__spot-value--tick-down')

        act(() => {
            rerender(<Header marketStatus="OPEN" spot={710.08} />)
        })

        expect(spotValue.className).toContain('l4-header__spot-value--down')
        expect(spotValue.className).not.toContain('l4-header__spot-value--tick-down')
    })
})

import { cleanup, render, screen } from '@testing-library/react'
import { useDashboardStore } from '../../store/dashboardStore'
import { MmFlowCard } from '../right/MmFlowCard'

afterEach(() => {
    cleanup()
    useDashboardStore.setState({ payload: null })
})

describe('MmFlowCard', () => {
    it('renders unavailable state when no metrics exist', () => {
        render(<MmFlowCard />)

        expect(screen.getByText('MM FLOW')).toBeInTheDocument()
        expect(screen.getByText('UNAVAILABLE')).toBeInTheDocument()
        expect(screen.getByText('No institutional flow metrics')).toBeInTheDocument()
    })

    it('renders metrics from stable prop contract', () => {
        render(
            <MmFlowCard
                preferProp
                metrics={{
                    net_delta_exposure_live: -22000,
                    net_gamma_exposure_live: 3300,
                    residual_delta_after_netting: -1800,
                    oi_participation_ratio_live: 0.27,
                    flow_suppression_bias: -5500,
                    flow_dominance_ratio: -0.09,
                    midpoint_tickrule_count: 8,
                    condition_filtered_count: 5,
                    complex_spread_count: 3,
                }}
            />
        )

        expect(screen.getByText('EXPANSIVE')).toBeInTheDocument()
        expect(screen.getByText('-22.00K')).toBeInTheDocument()
        expect(screen.getByText('+3.30K')).toBeInTheDocument()
        expect(screen.getByText('27.0%')).toBeInTheDocument()
        expect(screen.getByText('MID +8')).toBeInTheDocument()
        expect(screen.getByText('FLT +5')).toBeInTheDocument()
        expect(screen.getByText('SPD +3')).toBeInTheDocument()
    })
})

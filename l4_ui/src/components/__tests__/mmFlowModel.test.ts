import type { DashboardPayload } from '../../types/dashboard'
import { deriveMmFlowMetrics, deriveMmFlowView } from '../right/mmFlowModel'

function makePayload(mmFlow: Record<string, unknown>): DashboardPayload {
    return {
        type: 'dashboard_update',
        timestamp: '2026-04-16T20:00:00Z',
        spot: 530.5,
        agent_g: {
            agent: 'agent_g',
            signal: 'NEUTRAL',
            as_of: '2026-04-16T20:00:00Z',
            data: {
                fused_signal: {
                    direction: 'NEUTRAL',
                    confidence: 0.5,
                    weights: {},
                    regime: 'NORMAL',
                    iv_regime: 'NORMAL',
                    gex_intensity: 'LOW',
                    explanation: 'test',
                    components: {},
                    mm_flow: mmFlow,
                },
            },
        },
    } as unknown as DashboardPayload
}

describe('mmFlowModel', () => {
    it('derives metrics from fused_signal.mm_flow and formats suppressive view', () => {
        const payload = makePayload({
            net_delta_exposure_live: 210500,
            net_gamma_exposure_live: -10500,
            residual_delta_after_netting: 5250,
            oi_participation_ratio_live: 0.34,
            flow_suppression_bias: 9125,
            flow_dominance_ratio: 0.12,
            midpoint_tickrule_count: 11,
            condition_filtered_count: 3,
            complex_spread_count: 2,
        })

        const metrics = deriveMmFlowMetrics(payload)
        const view = deriveMmFlowView(metrics)

        expect(metrics?.flow_dominance_ratio).toBe(0.12)
        expect(view?.directionLabel).toBe('SUPPRESSIVE')
        expect(view?.netDelta).toBe('+210.50K')
        expect(view?.netGamma).toBe('-10.50K')
        expect(view?.oiParticipation).toBe('34.0%')
        expect(view?.midpointCount).toBe('+11')
    })

    it('returns null when mm flow contract is missing', () => {
        const payload = makePayload({})
        delete (payload.agent_g?.data as Record<string, unknown>).fused_signal

        expect(deriveMmFlowMetrics(payload)).toBeNull()
        expect(deriveMmFlowView(null)).toBeNull()
    })
})

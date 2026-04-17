import React, { memo } from 'react'
import { useDashboardStore, selectPayload } from '../../store/dashboardStore'
import { deriveMmFlowMetrics, deriveMmFlowView, type MmFlowMetrics } from './mmFlowModel'

interface Props {
    metrics?: MmFlowMetrics | null
    preferProp?: boolean
}

function directionClass(state: 'SUPPRESSIVE' | 'EXPANSIVE' | 'BALANCED'): string {
    if (state === 'SUPPRESSIVE') return 'badge-hollow-purple'
    if (state === 'EXPANSIVE') return 'badge-hollow-green'
    return 'badge-neutral'
}

export const MmFlowCard: React.FC<Props> = memo(({ metrics: propMetrics, preferProp = false }) => {
    const payload = useDashboardStore(selectPayload)
    const storeMetrics = deriveMmFlowMetrics(payload)
    const metrics = preferProp ? (propMetrics ?? storeMetrics) : (storeMetrics ?? propMetrics)
    const view = deriveMmFlowView(metrics ?? null)

    if (!view) {
        return (
            <div className="border-t border-bg-border" style={{ padding: 'var(--l4-panel-pad)' }}>
                <div className="flex items-center justify-between mb-1">
                    <span className="section-header">MM FLOW</span>
                    <span className="badge badge-neutral px-1 py-0!" style={{ fontSize: 'var(--l4-font-8)' }}>UNAVAILABLE</span>
                </div>
                <div className="mono text-text-secondary" style={{ fontSize: 'var(--l4-font-10)' }}>No institutional flow metrics</div>
            </div>
        )
    }

    return (
        <div className="border-t border-bg-border space-y-1" style={{ padding: 'var(--l4-panel-pad)' }}>
            <div className="flex items-center justify-between">
                <span className="section-header">MM FLOW</span>
                <span className={`badge px-1 py-0! ${directionClass(view.directionLabel)}`} style={{ fontSize: 'var(--l4-font-8)' }}>
                    {view.directionLabel}
                </span>
            </div>

            <div className="grid grid-cols-2 gap-1 mono" style={{ fontSize: 'var(--l4-font-10)' }}>
                <div className="text-text-secondary">NetΔ</div><div className="text-right text-text-primary">{view.netDelta}</div>
                <div className="text-text-secondary">NetΓ</div><div className="text-right text-text-primary">{view.netGamma}</div>
                <div className="text-text-secondary">ResidualΔ</div><div className="text-right text-text-primary">{view.residualDelta}</div>
                <div className="text-text-secondary">Suppression</div><div className="text-right text-text-primary">{view.suppressionBias}</div>
                <div className="text-text-secondary">Dominance</div><div className="text-right text-text-primary">{view.dominanceRatio}</div>
                <div className="text-text-secondary">OI Part.</div><div className="text-right text-text-primary">{view.oiParticipation}</div>
            </div>

            <div className="flex gap-2 mono text-text-secondary" style={{ fontSize: 'var(--l4-font-9)' }}>
                <span>MID {view.midpointCount}</span>
                <span>FLT {view.filteredCount}</span>
                <span>SPD {view.spreadCount}</span>
            </div>
        </div>
    )
})

MmFlowCard.displayName = 'MmFlowCard'

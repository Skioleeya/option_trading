/**
 * SkewDynamics — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { AlertCircle } from 'lucide-react'
import { useDashboardStore, selectUiStateSkewDynamics } from '../../store/dashboardStore'
import type { SkewDynamicsState } from '../../types/dashboard'
import { normalizeSkewDynamicsState } from './skewDynamicsModel'

interface Props {
    uiState?: SkewDynamicsState | null
    preferProp?: boolean
}

export const SkewDynamics: React.FC<Props> = memo(({ uiState: propState, preferProp = false }) => {
    const storeState = useDashboardStore(selectUiStateSkewDynamics)
    const state = normalizeSkewDynamicsState(preferProp ? (propState ?? storeState) : (storeState ?? propState))

    return (
        <div className="border-t border-bg-border p-2">
            <div className="flex items-center justify-between mb-1">
                <span className="section-header">SKEW DYNAMICS</span>
                <span className="section-header text-text-muted">IV SKEW ANALYSIS</span>
            </div>
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                    <div className={`w-5 h-5 rounded flex items-center justify-center border ${state.border_class} ${state.bg_class} ${state.shadow_class}`}>
                        <AlertCircle size={10} className="text-text-secondary" />
                    </div>
                    <div>
                        <div className="section-header">IV SKEW</div>
                        <div className={`badge ${state.badge} text-[9px] px-1 py-0! tracking-wider`}>
                            {state.state_label}
                        </div>
                    </div>
                </div>
                <span className={`mono text-xl font-bold ${state.color_class}`}>{state.value}</span>
            </div>
        </div>
    )
})

SkewDynamics.displayName = 'SkewDynamics'

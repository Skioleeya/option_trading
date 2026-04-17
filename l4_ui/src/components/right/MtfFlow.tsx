/**
 * MtfFlow — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { useDashboardStore, selectUiStateMtfFlow } from '../../store/dashboardStore'
import type { MtfFlowState } from '../../types/dashboard'
import { normalizeMtfFlowState } from './mtfFlowModel'

interface Props {
    uiState?: MtfFlowState | null
    preferProp?: boolean
}

export const MtfFlow: React.FC<Props> = memo(({ uiState: propState, preferProp = false }) => {
    const storeState = useDashboardStore(selectUiStateMtfFlow)
    const s = normalizeMtfFlowState(preferProp ? (propState ?? storeState) : (storeState ?? propState))

    const timeframes = [
        { label: '1M', data: s.m1 },
        { label: '5M', data: s.m5 },
        { label: '15M', data: s.m15 },
    ]

    return (
        <div className="border-t border-bg-border" style={{ padding: 'var(--l4-panel-pad)' }}>
            <div className="flex items-center justify-between mb-1.5">
                <span className="font-bold tracking-wider text-text-primary" style={{ fontSize: 'var(--l4-font-10)' }}>MTF FLOW</span>
                <span className={`font-bold mono ${s.alignClass}`} style={{ fontSize: 'var(--l4-font-9)' }}>{s.alignLabel}</span>
            </div>

            <div className="grid grid-cols-3" style={{ gap: 'var(--l4-panel-gap)' }}>
                {timeframes.map(({ label, data }) => (
                    <div key={label}
                        className={`flex flex-col items-center gap-0.5 border rounded transition-all duration-500 bg-white/[0.03] ${data.tokens.borderColor}`}
                        style={{ padding: 'var(--l4-card-pad-tight) var(--l4-card-pad)' }}>
                        <div className="flex items-center gap-1">
                            <span className="mono font-bold text-text-secondary" style={{ fontSize: 'var(--l4-font-10)' }}>{label}</span>
                            <div className={`w-2 h-2 rounded-full ${data.tokens.dotColor} ${data.tokens.shadowClass} ${data.tokens.animateClass} transition-all duration-500`} />
                        </div>
                        <span className={`mono font-bold ${data.tokens.textColor}`} style={{ fontSize: 'var(--l4-font-8)' }}>
                            {Math.round(data.kinetic_level * 100)}%
                        </span>
                        <span className={`font-mono ${data.tokens.textColor} opacity-80`} style={{ fontSize: 'var(--l4-font-8)' }}>{data.tokens.regimeLabel}</span>
                    </div>
                ))}
            </div>

            <div className="mt-1.5 flex items-center gap-1.5">
                <span className="text-text-muted" style={{ fontSize: 'var(--l4-font-8)' }}>CONSENSUS</span>
                <span className={`font-bold mono ${s.alignClass}`} style={{ fontSize: 'var(--l4-font-8)' }}>{s.consensusLabel}</span>
                <span className="font-bold text-text-secondary mono" style={{ fontSize: 'var(--l4-font-8)' }}>{s.consensusPercent}%</span>
            </div>
        </div>
    )
})

MtfFlow.displayName = 'MtfFlow'

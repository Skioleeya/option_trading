/**
 * MtfFlow — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { useDashboardStore, selectUiStateMtfFlow } from '../../store/dashboardStore'
import type { MtfFlowState } from '../../types/dashboard'
import type { FlowState } from './mtfFlowModel'
import { normalizeMtfFlowState } from './mtfFlowModel'

interface Props { uiState?: MtfFlowState | null }

const CONSENSUS_BAR: Record<FlowState, string> = {
    1: 'bg-accent-red',
    0: 'bg-zinc-600',
    [-1]: 'bg-accent-green',
}

export const MtfFlow: React.FC<Props> = memo(({ uiState: propState }) => {
    const storeState = useDashboardStore(selectUiStateMtfFlow)
    const s = normalizeMtfFlowState(storeState ?? propState)

    const timeframes = [
        { label: '1M', data: s.m1 },
        { label: '5M', data: s.m5 },
        { label: '15M', data: s.m15 },
    ]

    return (
        <div className="border-t border-bg-border p-2">
            <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-bold tracking-wider text-text-primary">MTF FLOW</span>
                <span className={`text-[9px] font-bold mono ${s.alignClass}`}>{s.alignLabel}</span>
            </div>

            <div className="grid grid-cols-3 gap-1">
                {timeframes.map(({ label, data }) => (
                    <div key={label}
                        className={`flex flex-col items-center gap-0.5 px-2 py-1.5 border rounded transition-all duration-500 bg-white/[0.03] ${data.tokens.borderColor}`}>
                        <div className="flex items-center gap-1">
                            <span className="mono text-[10px] font-bold text-text-secondary">{label}</span>
                            <div className={`w-2 h-2 rounded-full ${data.tokens.dotColor} ${data.tokens.shadowClass} ${data.tokens.animateClass} transition-all duration-500`} />
                        </div>
                        <div className="w-full h-[2px] bg-white/5 rounded-full overflow-hidden mt-0.5">
                            <div className={`h-full rounded-full transition-all duration-700 ${data.tokens.barColor}`} style={{ width: `${Math.round(data.kinetic_level * 100)}%` }} />
                        </div>
                        <span className={`text-[8px] font-mono ${data.tokens.textColor} opacity-80`}>{data.tokens.regimeLabel}</span>
                    </div>
                ))}
            </div>

            <div className="mt-1.5 flex items-center gap-1.5">
                <span className="text-[8px] text-text-muted">{s.consensusLabel}</span>
                <div className="flex-1 h-[2px] bg-white/5 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-700 ${CONSENSUS_BAR[s.consensusState]}`}
                        style={{ width: `${s.consensusPercent}%` }} />
                </div>
                <span className="text-[8px] font-bold text-text-secondary mono">{s.consensusPercent}%</span>
            </div>
        </div>
    )
})

MtfFlow.displayName = 'MtfFlow'

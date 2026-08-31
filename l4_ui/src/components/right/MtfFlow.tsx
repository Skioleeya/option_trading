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

function toPercent(value: number): number {
    const pct = Math.round(value * 100)
    if (pct < 0) return 0
    if (pct > 100) return 100
    return pct
}

export const MtfFlow: React.FC<Props> = memo(({ uiState: propState, preferProp = false }) => {
    const storeState = useDashboardStore(selectUiStateMtfFlow)
    const s = normalizeMtfFlowState(preferProp ? (propState ?? storeState) : (storeState ?? propState))
    const consensusBarClass = s.consensusState === 1
        ? 'bg-accent-red'
        : s.consensusState === -1
            ? 'bg-accent-green'
            : 'bg-zinc-600'

    const timeframes = [
        { key: 'm1', label: '1M', data: s.m1 },
        { key: 'm5', label: '5M', data: s.m5 },
        { key: 'm15', label: '15M', data: s.m15 },
    ]

    return (
        <div className="l4-mtf-flow border-t border-bg-border" style={{ padding: 'var(--l4-panel-pad)' }}>
            <div className="flex items-center justify-between mb-1.5">
                <span className="font-bold tracking-wider text-text-primary" style={{ fontSize: 'var(--l4-font-10)' }}>MTF FLOW</span>
                <span className={`font-bold mono ${s.alignClass}`} style={{ fontSize: 'var(--l4-font-9)' }}>{s.alignLabel}</span>
            </div>

            <div className="grid grid-cols-3" style={{ gap: 'var(--l4-panel-gap)' }}>
                {timeframes.map(({ key, label, data }) => {
                    const kineticPercent = toPercent(data.kinetic_level)
                    return (
                    <div key={label}
                        className={`flex flex-col items-center gap-0.5 border rounded bg-white/[0.03] ${data.tokens.borderColor}`}
                        style={{ padding: 'var(--l4-card-pad-tight) var(--l4-card-pad)' }}>
                        <div className="flex items-center gap-1">
                            <span className="mono font-bold text-text-secondary" style={{ fontSize: 'var(--l4-font-10)' }}>{label}</span>
                            <div className={`w-2 h-2 rounded-full ${data.tokens.dotColor}`} />
                        </div>
                        <div
                            role="progressbar"
                            aria-label={`${label} kinetic`}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-valuenow={kineticPercent}
                            data-testid={`mtf-${key}-bar`}
                            className="relative w-full overflow-hidden rounded-full border border-white/10 bg-white/10"
                            style={{ height: '6px' }}
                        >
                            <div
                                className={`h-full rounded-full ${data.tokens.dotColor}`}
                                style={{ width: `${kineticPercent}%` }}
                            />
                        </div>
                        <span className={`font-mono ${data.tokens.textColor} opacity-80`} style={{ fontSize: 'var(--l4-font-8)' }}>{data.tokens.regimeLabel}</span>
                    </div>
                    )
                })}
            </div>

            <div className="mt-1.5 grid items-center" style={{ gridTemplateColumns: 'auto auto 1fr', gap: '6px' }}>
                <span className="text-text-muted" style={{ fontSize: 'var(--l4-font-8)' }}>CONSENSUS</span>
                <span className={`font-bold mono ${s.alignClass}`} style={{ fontSize: 'var(--l4-font-8)' }}>{s.consensusLabel}</span>
                <div
                    role="progressbar"
                    aria-label="CONSENSUS kinetic"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={s.consensusPercent}
                    data-testid="mtf-consensus-bar"
                    className="relative w-full overflow-hidden rounded-full border border-white/10 bg-white/10"
                    style={{ height: '6px' }}
                >
                    <div
                        className={`h-full rounded-full ${consensusBarClass}`}
                        style={{ width: `${s.consensusPercent}%` }}
                    />
                </div>
            </div>
        </div>
    )
})

MtfFlow.displayName = 'MtfFlow'

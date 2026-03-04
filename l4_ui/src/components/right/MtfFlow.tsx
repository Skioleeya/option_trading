/**
 * MtfFlow — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { useDashboardStore } from '../../store/dashboardStore'

const selectMtfFlow = (s: ReturnType<typeof useDashboardStore.getState>) =>
    s.payload?.agent_g?.data?.ui_state?.mtf_flow ?? null

interface TFState {
    direction: string; regime: string; regime_label: string
    z: number; strength: number; tier: string
    dot_color: string; text_color: string; shadow: string; border: string; animate: string
}

type MtfState = { m1: TFState; m5: TFState; m15: TFState; consensus: string; strength: number; alignment: number; align_label: string; align_color: string } | null

interface Props { uiState?: MtfState }

const DEFAULT_TF: TFState = { direction: 'NEUTRAL', regime: 'NOISE', regime_label: '—', z: 0, strength: 0, tier: 'WEAK', dot_color: 'bg-zinc-700', text_color: 'text-text-secondary', shadow: 'shadow-none', border: 'border-bg-border', animate: '' }
const DEFAULT_STATE: NonNullable<MtfState> = { m1: DEFAULT_TF, m5: DEFAULT_TF, m15: DEFAULT_TF, consensus: 'NEUTRAL', strength: 0, alignment: 0, align_label: 'DIVERGE', align_color: 'text-text-secondary' }

export const MtfFlow: React.FC<Props> = memo(({ uiState: propState }) => {
    const storeState = useDashboardStore(selectMtfFlow)
    const s = (storeState ?? propState ?? DEFAULT_STATE) as NonNullable<MtfState>

    const timeframes = [
        { label: '1M', data: s.m1 },
        { label: '5M', data: s.m5 },
        { label: '15M', data: s.m15 },
    ]

    return (
        <div className="border-t border-bg-border p-2">
            <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-bold tracking-wider text-text-primary">MTF FLOW</span>
                <span className={`text-[9px] font-bold mono ${s.align_color}`}>{s.align_label}</span>
            </div>

            <div className="grid grid-cols-3 gap-1">
                {timeframes.map(({ label, data }) => (
                    <div key={label}
                        className={`flex flex-col items-center gap-0.5 px-2 py-1.5 border rounded transition-all duration-500 bg-white/[0.03] ${data.border}`}>
                        <div className="flex items-center gap-1">
                            <span className="mono text-[10px] font-bold text-text-secondary">{label}</span>
                            <div className={`w-2 h-2 rounded-full ${data.dot_color} ${data.shadow} ${data.animate} transition-all duration-500`} />
                        </div>
                        <div className="w-full h-[2px] bg-white/5 rounded-full overflow-hidden mt-0.5">
                            <div className={`h-full rounded-full transition-all duration-700 ${data.dot_color}`} style={{ width: `${Math.round(data.strength * 100)}%` }} />
                        </div>
                        <span className={`text-[8px] font-mono ${data.text_color} opacity-80`}>{data.regime_label}</span>
                    </div>
                ))}
            </div>

            <div className="mt-1.5 flex items-center gap-1.5">
                <span className="text-[8px] text-text-muted">CONSENSUS</span>
                <div className="flex-1 h-[2px] bg-white/5 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-700 ${s.consensus === 'BULLISH' ? 'bg-accent-red' : s.consensus === 'BEARISH' ? 'bg-accent-green' : 'bg-zinc-600'}`}
                        style={{ width: `${Math.round(s.strength * 100)}%` }} />
                </div>
                <span className="text-[8px] font-bold text-text-secondary mono">{Math.round(s.strength * 100)}%</span>
            </div>
        </div>
    )
})

MtfFlow.displayName = 'MtfFlow'

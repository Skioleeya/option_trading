/**
 * DecisionEngine — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { Target, Activity, TrendingUp, BarChart3 } from 'lucide-react'
import type { FusedSignal } from '../../types/dashboard'
import { useDashboardStore, selectFused } from '../../store/dashboardStore'
import { normalizeBadgeToken } from '../left/microStatsTheme'
import {
    confidenceToPercent,
    formatRegimeLabel,
    normalizeDecisionTone,
    resolveDirectionClasses,
    resolveGexIntensityBadgeClass,
    resolveWeightBarWidth,
    resolveWeightPercent,
} from './decisionEngineModel'

interface Props {
    fused?: FusedSignal | null
}

const selectNetGexBadge = (s: ReturnType<typeof useDashboardStore.getState>) =>
    s.payload?.agent_g?.data?.ui_state?.micro_stats?.net_gex ?? null

function stripGexPrefix(label: string): string {
    return label.replace(/^gex\s+/i, '').trim()
}

const Zap: React.FC = () => (
    <svg width="8" height="8" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2.5" className="text-text-secondary">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
)

export const DecisionEngine: React.FC<Props> = memo(({ fused: propFused }) => {
    const storeFused = useDashboardStore(selectFused)
    const storeNetGex = useDashboardStore(selectNetGexBadge)
    const fused = storeFused ?? propFused ?? null

    const dir = normalizeDecisionTone(fused?.direction)
    const conf = confidenceToPercent(fused?.confidence)
    const dirTheme = resolveDirectionClasses(dir)
    const comps = fused?.components ?? {}
    const regime = fused?.regime ?? ''
    const gexInt = fused?.gex_intensity ?? ''
    const netGexLabelRaw = String(storeNetGex?.label ?? '').trim()
    const hasNetGex = netGexLabelRaw !== '' && netGexLabelRaw !== '—'
    const gexLabelCore = hasNetGex
        ? stripGexPrefix(netGexLabelRaw)
        : formatRegimeLabel(gexInt)
    const gexBadgeClass = hasNetGex
        ? normalizeBadgeToken(storeNetGex?.badge, gexLabelCore)
        : resolveGexIntensityBadgeClass(gexInt)
    const gexLabel = gexLabelCore ? `GEX ${gexLabelCore}` : ''

    const quadrants = [
        { key: 'momentum_signal', label: 'MOMENTUM', icon: <TrendingUp size={9} className="text-text-secondary" /> },
        { key: 'trap_detector', label: 'TRAPS', icon: <Target size={9} className="text-text-secondary" /> },
        { key: 'flow_analyzer', label: 'FLOW DYN', icon: <Zap /> },
        { key: 'micro_flow', label: 'MICRO FLOW', icon: <BarChart3 size={9} className="text-text-secondary" /> },
        { key: 'iv_regime', label: 'IV REGIME', icon: <Activity size={9} className="text-text-secondary" /> },
    ]


    return (
        <div className="p-2 space-y-1.5">
            <div className="flex items-center justify-between">
                <span className="section-header text-[10px]">DECISION ENGINE</span>
                <span className="section-header text-text-muted text-[10px]">FUSION</span>
            </div>

            <div className={`flex items-center justify-between px-2 py-1 rounded border ${dirTheme.banner} transition-all duration-500`}>
                <div className="flex items-center gap-1.5">
                    <div className={`w-2 h-2 rounded-full ${dirTheme.dot} transition-all duration-500`} />
                    <span className={`text-[11px] font-black tracking-widest ${dirTheme.text}`}>{dir}</span>
                </div>
                <span className={`mono text-[11px] font-bold ${dirTheme.text}`}>{conf}%</span>
            </div>

            <div className="h-[2px] w-full bg-white/5 rounded-full overflow-hidden">
                <div className={`h-full rounded-full transition-all duration-700 ${dirTheme.bar}`} style={{ width: `${conf}%` }} />
            </div>

            {(regime || gexLabel) && (
                <div className="flex gap-1 flex-wrap">
                    {regime && <span className="badge badge-neutral text-[7px] py-0 px-1">{formatRegimeLabel(regime)}</span>}
                    {gexLabel && (
                        <span className={`badge text-[7px] py-0 px-1 ${gexBadgeClass}`}>
                            {gexLabel}
                        </span>
                    )}
                </div>
            )}

            <div className="grid grid-cols-2 gap-1">
                {quadrants.map((q, idx) => {
                    const comp = comps[q.key]
                    const qDir = normalizeDecisionTone(comp?.direction)
                    const qConf = confidenceToPercent(comp?.confidence)
                    const qWt = resolveWeightPercent(fused, q.key)
                    const qTheme = resolveDirectionClasses(qDir)
                    const qBarWidth = resolveWeightBarWidth(qWt)
                    const isFullWidth = quadrants.length % 2 !== 0 && idx === quadrants.length - 1

                    return (
                        <div key={q.key} className={`bg-bg-card rounded p-1 border border-bg-border ${isFullWidth ? 'col-span-2' : ''}`}>
                            <div className="flex items-center justify-between mb-0.5">
                                <div className="flex items-center gap-1 section-header text-[8px]">
                                    {React.cloneElement(q.icon as React.ReactElement, { size: 8, className: 'text-text-secondary' })}
                                    {q.label}
                                </div>
                                <div className="flex items-center gap-1">
                                    <div className={`w-1.5 h-1.5 rounded-full ${qTheme.dot} transition-all duration-500`} />
                                    <span className={`mono text-[9px] font-bold ${qTheme.text}`}>{qWt}%</span>
                                </div>
                            </div>
                            <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                <div className={`h-full rounded-full transition-all duration-500 ${qTheme.bar}`} style={{ width: `${qBarWidth}%` }} />
                            </div>
                            <div className={`text-[7px] mono mt-0.5 ${qTheme.text} opacity-60 flex justify-between`}>
                                <span>conf {qConf}%</span>
                                {q.key === 'micro_flow' && fused && (fused.raw_vpin !== undefined || fused.raw_bbo_imb !== undefined) && (
                                    <span className="select-text text-text-secondary/70">V:{typeof fused.raw_vpin === 'number' ? (fused.raw_vpin as number).toFixed(4) : fused.raw_vpin ?? '-'} BBO:{typeof fused.raw_bbo_imb === 'number' ? (fused.raw_bbo_imb as number).toFixed(4) : fused.raw_bbo_imb ?? '-'}</span>
                                )}
                                {q.key === 'flow_analyzer' && fused && (fused.raw_vol_accel !== undefined) && (
                                    <span className="select-text text-text-secondary/70">ACC:{typeof fused.raw_vol_accel === 'number' ? (fused.raw_vol_accel as number).toFixed(4) : fused.raw_vol_accel ?? '-'}</span>
                                )}
                                {isFullWidth && <span className="opacity-40 italic">Paper 3 High Leverage Predictor</span>}
                            </div>
                        </div>
                    )
                })}
            </div>

        </div>
    )
})

DecisionEngine.displayName = 'DecisionEngine'

/**
 * DecisionEngine — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { Target, Activity, TrendingUp, BarChart3 } from 'lucide-react'
import type { FusedSignal } from '../../types/dashboard'
import { useDashboardStore, selectFused, selectUiStateMicroStats } from '../../store/dashboardStore'
import { normalizeBadgeToken } from '../left/microStatsTheme'
import {
    confidenceToPercent,
    formatRegimeLabel,
    normalizeDecisionTone,
    resolveDirectionClasses,
    resolveGexIntensityBadgeClass,
    resolveWeightPercent,
} from './decisionEngineModel'
import type { NetGexBadgeState } from './rightPanelModel'

interface Props {
    fused?: FusedSignal | null
    netGex?: NetGexBadgeState | null
    preferProp?: boolean
}

function stripGexPrefix(label: string): string {
    return label.replace(/^gex\s+/i, '').trim()
}

const Zap: React.FC = () => (
    <svg width="8" height="8" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2.5" className="text-text-secondary">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
)

export const DecisionEngine: React.FC<Props> = memo(({ fused: propFused, netGex: propNetGex, preferProp = false }) => {
    const storeFused = useDashboardStore(selectFused)
    const storeNetGex = useDashboardStore(selectUiStateMicroStats)?.net_gex ?? null
    const fused = preferProp
        ? (propFused ?? storeFused ?? null)
        : (storeFused ?? propFused ?? null)
    const netGex = preferProp
        ? (propNetGex ?? storeNetGex)
        : (storeNetGex ?? propNetGex)

    const dir = normalizeDecisionTone(fused?.direction)
    const conf = confidenceToPercent(fused?.confidence)
    const dirTheme = resolveDirectionClasses(dir)
    const comps = fused?.components ?? {}
    const regime = fused?.regime ?? ''
    const gexInt = fused?.gex_intensity ?? ''
    const netGexLabelRaw = String(netGex?.label ?? '').trim()
    const hasNetGex = netGexLabelRaw !== '' && netGexLabelRaw !== '—'
    const gexLabelCore = hasNetGex
        ? stripGexPrefix(netGexLabelRaw)
        : formatRegimeLabel(gexInt)
    const gexBadgeClass = hasNetGex
        ? normalizeBadgeToken(netGex?.badge, gexLabelCore)
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
        <div className="l4-decision-engine space-y-1.5" style={{ padding: 'var(--l4-panel-pad)' }}>
            <div className="flex items-center justify-between">
                <span className="section-header" style={{ fontSize: 'var(--l4-font-10)' }}>DECISION ENGINE</span>
                <span className="section-header text-text-muted" style={{ fontSize: 'var(--l4-font-10)' }}>FUSION</span>
            </div>

            <div className={`flex items-center justify-between rounded border ${dirTheme.banner}`} style={{ padding: 'var(--l4-card-pad-tight) var(--l4-card-pad)' }}>
                <div className="flex items-center gap-1.5">
                    <div className={`w-2 h-2 rounded-full ${dirTheme.dot}`} />
                    <span className={`font-black tracking-widest ${dirTheme.text}`} style={{ fontSize: 'var(--l4-font-11)' }}>{dir}</span>
                </div>
                <span className={`mono font-bold ${dirTheme.text}`} style={{ fontSize: 'var(--l4-font-11)' }}>{conf}%</span>
            </div>

            {(regime || gexLabel) && (
                <div className="flex gap-1 flex-wrap">
                    {regime && <span className="badge badge-neutral py-0 px-1" style={{ fontSize: 'var(--l4-font-7)' }}>{formatRegimeLabel(regime)}</span>}
                    {gexLabel && (
                        <span className={`badge py-0 px-1 ${gexBadgeClass}`} style={{ fontSize: 'var(--l4-font-7)' }}>
                            {gexLabel}
                        </span>
                    )}
                </div>
            )}

            <div className="grid grid-cols-2" style={{ gap: 'var(--l4-panel-gap)' }}>
                {quadrants.map((q, idx) => {
                    const comp = comps[q.key]
                    const qDir = normalizeDecisionTone(comp?.direction)
                    const qConf = confidenceToPercent(comp?.confidence)
                    const qWt = resolveWeightPercent(fused, q.key)
                    const qTheme = resolveDirectionClasses(qDir)
                    const isFullWidth = quadrants.length % 2 !== 0 && idx === quadrants.length - 1

                    return (
                        <div
                            key={q.key}
                            className={`bg-bg-card border border-bg-border ${isFullWidth ? 'col-span-2' : ''}`}
                            style={{ borderRadius: 'var(--l4-card-radius)', padding: 'var(--l4-card-pad-tight)' }}
                        >
                            <div className="flex items-center justify-between mb-0.5">
                                <div className="flex items-center gap-1 section-header" style={{ fontSize: 'var(--l4-font-8)' }}>
                                    {React.cloneElement(q.icon as React.ReactElement, { size: 8, className: 'text-text-secondary' })}
                                    {q.label}
                                </div>
                                <div className="flex items-center gap-1">
                                    <div className={`w-1.5 h-1.5 rounded-full ${qTheme.dot}`} />
                                    <span className={`mono font-bold ${qTheme.text}`} style={{ fontSize: 'var(--l4-font-9)' }}>{qWt}%</span>
                                </div>
                            </div>
                            <div className={`mono mt-0.5 ${qTheme.text} opacity-60 flex justify-between`} style={{ fontSize: 'var(--l4-font-7)' }}>
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

/**
 * DecisionEngine — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { Target, Activity, TrendingUp, BarChart3 } from 'lucide-react'
import type { FusedSignal } from '../../types/dashboard'
import { useDashboardStore, selectFused } from '../../store/dashboardStore'

interface Props {
    fused?: FusedSignal | null
}

const DIR_DOT: Record<string, string> = {
    BULLISH: 'bg-accent-red  shadow-[0_0_6px_rgba(255,77,79,0.5)]',
    BEARISH: 'bg-accent-green shadow-[0_0_6px_rgba(0,214,143,0.5)]',
    NEUTRAL: 'bg-zinc-600',
}
const DIR_BAR: Record<string, string> = {
    BULLISH: 'bg-accent-red', BEARISH: 'bg-accent-green', NEUTRAL: 'bg-zinc-600',
}
const DIR_TEXT: Record<string, string> = {
    BULLISH: 'text-accent-red', BEARISH: 'text-accent-green', NEUTRAL: 'text-text-secondary',
}
const BANNER_BG: Record<string, string> = {
    BULLISH: 'bg-red-950/40  border-red-500/30',
    BEARISH: 'bg-emerald-950/40 border-emerald-500/30',
    NEUTRAL: 'bg-zinc-900/40  border-zinc-700/30',
}

const fmtRegime = (r: string) => r.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1').trim().toUpperCase()
const truncate = (s: string, n = 75) => s.length > n ? s.slice(0, n - 1) + '…' : s

const Zap: React.FC = () => (
    <svg width="8" height="8" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2.5" className="text-text-secondary">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
)

export const DecisionEngine: React.FC<Props> = memo(({ fused: propFused }) => {
    const storeFused = useDashboardStore(selectFused)
    const fused = storeFused ?? propFused ?? null

    const dir = fused?.direction ?? 'NEUTRAL'
    const conf = Math.round((fused?.confidence ?? 0) * 100)
    const weights = fused?.weights ?? { iv: 0, wall: 0, vanna: 0, mtf: 0, vib: 0 }
    const comps = fused?.components ?? {}
    const regime = fused?.regime ?? ''
    const gexInt = fused?.gex_intensity ?? ''
    const explanation = fused?.explanation ?? ''

    const quadrants = [
        { key: 'iv', label: 'IV VEL', icon: <Zap /> },
        { key: 'wall', label: 'WALL DYN', icon: <Target size={9} className="text-text-secondary" /> },
        { key: 'vanna', label: 'VANNA', icon: <Activity size={9} className="text-text-secondary" /> },
        { key: 'mtf', label: 'MTF', icon: <TrendingUp size={9} className="text-text-secondary" /> },
        { key: 'vib', label: 'C/P VOL', icon: <BarChart3 size={9} className="text-text-secondary" /> },
    ]

    return (
        <div className="p-2 space-y-1.5">
            <div className="flex items-center justify-between">
                <span className="section-header text-[10px]">DECISION ENGINE</span>
                <span className="section-header text-text-muted text-[10px]">FUSION</span>
            </div>

            <div className={`flex items-center justify-between px-2 py-1 rounded border ${BANNER_BG[dir]} transition-all duration-500`}>
                <div className="flex items-center gap-1.5">
                    <div className={`w-2 h-2 rounded-full ${DIR_DOT[dir]} transition-all duration-500`} />
                    <span className={`text-[11px] font-black tracking-widest ${DIR_TEXT[dir]}`}>{dir}</span>
                </div>
                <span className={`mono text-[11px] font-bold ${DIR_TEXT[dir]}`}>{conf}%</span>
            </div>

            <div className="h-[2px] w-full bg-white/5 rounded-full overflow-hidden">
                <div className={`h-full rounded-full transition-all duration-700 ${DIR_BAR[dir]}`} style={{ width: `${conf}%` }} />
            </div>

            {(regime || gexInt) && (
                <div className="flex gap-1 flex-wrap">
                    {regime && <span className="badge badge-neutral text-[7px] py-0 px-1">{fmtRegime(regime)}</span>}
                    {gexInt && (
                        <span className={`badge text-[7px] py-0 px-1 ${gexInt.includes('NEGATIVE') ? 'badge-red-dim' : gexInt.includes('POSITIVE') ? 'badge-hollow-green' : 'badge-neutral'}`}>
                            GEX {fmtRegime(gexInt)}
                        </span>
                    )}
                </div>
            )}

            <div className="grid grid-cols-2 gap-1">
                {quadrants.map((q, idx) => {
                    const comp = comps[q.key]
                    const qDir = comp?.direction ?? 'NEUTRAL'
                    const qConf = Math.round((comp?.confidence ?? 0) * 100)
                    const qWt = Math.round((weights[q.key as keyof typeof weights] ?? 0) * 100)
                    const isFullWidth = quadrants.length % 2 !== 0 && idx === quadrants.length - 1

                    return (
                        <div key={q.key} className={`bg-bg-card rounded p-1 border border-bg-border ${isFullWidth ? 'col-span-2' : ''}`}>
                            <div className="flex items-center justify-between mb-0.5">
                                <div className="flex items-center gap-1 section-header text-[8px]">
                                    {React.cloneElement(q.icon as React.ReactElement, { size: 8, className: 'text-text-secondary' })}
                                    {q.label}
                                </div>
                                <div className="flex items-center gap-1">
                                    <div className={`w-1.5 h-1.5 rounded-full ${DIR_DOT[qDir]} transition-all duration-500`} />
                                    <span className={`mono text-[9px] font-bold ${DIR_TEXT[qDir]}`}>{qWt}%</span>
                                </div>
                            </div>
                            <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                <div className={`h-full rounded-full transition-all duration-500 ${DIR_BAR[qDir]}`} style={{ width: `${Math.max(qWt, 2)}%` }} />
                            </div>
                            <div className={`text-[7px] mono mt-0.5 ${DIR_TEXT[qDir]} opacity-60 flex justify-between`}>
                                <span>conf {qConf}%</span>
                                {isFullWidth && <span className="opacity-40 italic">Paper 3 High Leverage Predictor</span>}
                            </div>
                        </div>
                    )
                })}
            </div>

            {explanation && (
                <p className="text-[8px] mono text-text-secondary leading-tight truncate cursor-default opacity-80" title={explanation}>
                    {truncate(explanation, 75)}
                </p>
            )}
        </div>
    )
})

DecisionEngine.displayName = 'DecisionEngine'

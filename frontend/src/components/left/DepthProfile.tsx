import React from 'react'
import { fmtPrice } from '../../lib/utils'
import type { PerStrikeGex } from '../../types/dashboard'

interface Props {
    perStrikeGex: PerStrikeGex[]
    spot: number | null
    flipLevel: number | null
}

export const DepthProfile: React.FC<Props> = ({ perStrikeGex, spot, flipLevel }) => {
    if (!perStrikeGex.length) {
        return (
            <div className="flex items-center justify-center h-32 text-text-secondary section-header">
                NO DATA
            </div>
        )
    }

    const sorted = [...perStrikeGex].sort((a, b) => b.strike - a.strike)
    const spotVal = spot ?? sorted[Math.floor(sorted.length / 2)]?.strike ?? 0

    // Show ±8 strikes around spot
    const visibleStrikes = sorted.filter(s =>
        s.strike >= spotVal - 8 && s.strike <= spotVal + 8
    )

    const maxAbsGex = Math.max(
        ...visibleStrikes.map(s => Math.max(Math.abs(s.call_gex), Math.abs(s.put_gex))),
        1
    )

    const BAR_MAX_PX = 90 // max px each side

    return (
        <div className="overflow-y-auto px-1" style={{ maxHeight: '340px' }}>
            {/* Legend header */}
            <div className="flex items-center justify-between px-1 mb-0.5">
                <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-accent-green inline-block" />
                    <span className="section-header">Put</span>
                </div>
                <div className="flex items-center gap-1">
                    <span className="section-header">Call</span>
                    <span className="w-2 h-2 rounded-full bg-accent-red inline-block" />
                </div>
            </div>

            {/* Row for each strike */}
            <div className="space-y-px">
                {visibleStrikes.map((s) => {
                    const callWidth = Math.min((Math.abs(s.call_gex) / maxAbsGex) * BAR_MAX_PX, BAR_MAX_PX)
                    const putWidth = Math.min((Math.abs(s.put_gex) / maxAbsGex) * BAR_MAX_PX, BAR_MAX_PX)

                    const isSpot = spot != null && Math.abs(s.strike - spot) < 0.5
                    const isFlip = flipLevel != null && Math.abs(s.strike - flipLevel) < 0.5

                    const isDominantPut = Math.abs(s.put_gex) > Math.abs(s.call_gex)
                    const isDominantCall = Math.abs(s.call_gex) > Math.abs(s.put_gex)

                    return (
                        <div key={s.strike}>
                            <div
                                className={`flex items-center relative py-px ${isSpot ? 'bg-white/5' : ''
                                    }`}
                                style={{ minHeight: '16px' }}
                            >
                                {/* ── PUT bar (LEFT side, extends from center outward left) ── */}
                                <div
                                    className="flex items-center justify-end"
                                    style={{ width: `${BAR_MAX_PX}px`, minWidth: `${BAR_MAX_PX}px` }}
                                >
                                    <div
                                        className="h-4 rounded-sm bg-[#10b981]"
                                        style={{ width: `${putWidth}px` }}
                                    />
                                    {/* P label on inner edge of put bar */}
                                    {isDominantPut && putWidth > 20 && (
                                        <span className="mono text-2xs font-bold text-bg-primary ml-1 z-10">P</span>
                                    )}
                                </div>

                                {/* ── Strike CENTER ── */}
                                <div className="flex flex-col items-center" style={{ minWidth: '42px' }}>
                                    <div className="w-px bg-bg-border" style={{ height: '16px', position: 'absolute', left: '50%' }} />
                                    <span className={`mono text-2xs font-medium z-10 relative px-1 ${isSpot ? 'text-accent-amber font-bold' :
                                        isFlip ? 'text-accent-purple' :
                                            'text-text-secondary'
                                        }`}>
                                        {s.strike}
                                    </span>
                                </div>

                                {/* ── CALL bar (RIGHT side) ── */}
                                <div
                                    className="flex items-center"
                                    style={{ width: `${BAR_MAX_PX}px`, minWidth: `${BAR_MAX_PX}px` }}
                                >
                                    {/* C label on inner edge of call bar */}
                                    {isDominantCall && callWidth > 20 && (
                                        <span className="mono text-2xs font-bold text-bg-primary mr-1 z-10">C</span>
                                    )}
                                    <div
                                        className="h-4 rounded-sm bg-[#ef4444]"
                                        style={{ width: `${callWidth}px` }}
                                    />
                                    {/* SPOT label — only on spot row */}
                                    {isSpot && (
                                        <span className="mono text-2xs text-accent-amber font-bold ml-1 whitespace-nowrap">
                                            SPOT {fmtPrice(spot)}
                                        </span>
                                    )}
                                </div>
                            </div>

                            {/* FLIP dashed line — drawn as separator below flip strike */}
                            {isFlip && (
                                <div className="flex items-center" style={{ marginLeft: `${BAR_MAX_PX}px` }}>
                                    <div className="flex-1 border-t border-dashed border-accent-amber/60" />
                                    <span className="mono text-2xs text-accent-amber font-bold px-1">FLIP</span>
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

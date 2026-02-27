import React from 'react'
import { fmtGex, fmtPrice } from '../../lib/utils'

interface Props {
    netGex: number | null
    callWall: number | null
    flipLevel: number | null
    putWall: number | null
}

export const GexStatusBar: React.FC<Props> = ({ netGex, callWall, flipLevel, putWall }) => {
    return (
        <div className="flex items-center justify-center gap-6 px-4 py-1 border-t border-bg-border bg-bg-secondary"
            style={{ height: '28px' }}>
            {/* Net GEX */}
            <div className="flex items-center gap-1.5">
                <span className="section-header">NET GEX</span>
                <span className={`mono text-xs font-bold ${netGex == null ? 'text-text-secondary' :
                        netGex > 0 ? 'text-accent-green' : 'text-accent-red'
                    }`}>
                    {fmtGex(netGex)}
                </span>
            </div>

            <div className="w-px h-3 bg-bg-border" />

            {/* Call Wall */}
            <div className="flex items-center gap-1.5">
                <span className="section-header">CALL WALL</span>
                <span className="mono text-xs font-bold text-accent-red">
                    {fmtPrice(callWall)}
                </span>
            </div>

            <div className="w-px h-3 bg-bg-border" />

            {/* Flip */}
            <div className="flex items-center gap-1.5">
                <span className="section-header">FLIP</span>
                <span className="mono text-xs font-bold text-accent-amber">
                    {fmtPrice(flipLevel)}
                </span>
            </div>

            <div className="w-px h-3 bg-bg-border" />

            {/* Put Wall */}
            <div className="flex items-center gap-1.5">
                <span className="section-header">PUT WALL</span>
                <span className="mono text-xs font-bold text-accent-green">
                    {fmtPrice(putWall)}
                </span>
            </div>
        </div>
    )
}

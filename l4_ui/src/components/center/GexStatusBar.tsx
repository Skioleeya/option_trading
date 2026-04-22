/**
 * GexStatusBar — Phase 3: Zustand field-level selectors
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { fmtGex, fmtPrice } from '../../lib/utils'
import { Activity } from 'lucide-react'
import {
    useDashboardStore,
    selectNetGex,
    selectGammaWalls,
    selectFlipLevel,
} from '../../store/dashboardStore'
import { ASIAN_WALL_STYLE, normalizeGexStatus, resolveAsianGexTone } from './gexStatus'

interface Props {
    netGex?: number | null
    callWall?: number | null
    flipLevel?: number | null
    putWall?: number | null
}

export const GexStatusBar: React.FC<Props> = memo(({
    netGex: propNetGex,
    callWall: propCallWall,
    flipLevel: propFlipLevel,
    putWall: propPutWall,
}) => {
    const storeNetGex = useDashboardStore(selectNetGex)
    const storeGamma = useDashboardStore(selectGammaWalls)
    const storeFlipLevel = useDashboardStore(selectFlipLevel)

    const normalized = normalizeGexStatus({
        netGex: storeNetGex ?? propNetGex ?? null,
        callWall: storeGamma?.call_wall ?? propCallWall ?? null,
        putWall: storeGamma?.put_wall ?? propPutWall ?? null,
        flipLevel: storeFlipLevel ?? propFlipLevel ?? null,
    })
    const netGex = normalized.netGex
    const callWall = normalized.callWall
    const putWall = normalized.putWall
    const flipLevel = normalized.flipLevel

    const gexTone = resolveAsianGexTone(netGex)
    const gexColor = gexTone.textClass

    return (
        <div className="flex items-center bg-[#0d0d0f]/96 border border-[#3f3f46] rounded-full shadow-[0_0_24px_rgba(0,0,0,0.8)] font-sans overflow-hidden"
            style={{
                width: 'var(--l4-gex-bar-w)',
                height: 'var(--l4-gex-bar-h)',
                padding: '0 var(--l4-gex-pad-x)',
            }}>

            {/* NET GEX */}
            <div className="flex-1 flex items-center justify-center gap-2">
                <Activity size={14} className={gexColor} style={{ width: 'var(--l4-icon-md)', height: 'var(--l4-icon-md)' }} />
                <div className="flex flex-col leading-none">
                    <span className="font-bold tracking-[0.1em] text-[#52525b] uppercase" style={{ fontSize: 'var(--l4-font-8)' }}>Net GEX</span>
                    <span className={`font-mono font-black tracking-tight ${gexColor}`} style={{ fontSize: 'var(--l4-font-13)' }}>{fmtGex(netGex)}</span>
                </div>
            </div>

            <div className="w-[1px] bg-[#3f3f46] shrink-0" style={{ height: 'var(--l4-divider-h)' }} />

            {/* CALL WALL */}
            <div className="flex-1 flex items-center justify-center gap-2">
                <span className="font-bold tracking-[0.1em] text-[#71717a] uppercase whitespace-nowrap" style={{ fontSize: 'var(--l4-font-8)' }}>Call Wall</span>
                <span className={`px-1.5 py-[1px] rounded-[3px] font-mono font-black ${ASIAN_WALL_STYLE.call}`} style={{ fontSize: 'var(--l4-font-12)' }}>
                    {fmtPrice(callWall)}
                </span>
            </div>

            <div className="w-[1px] bg-[#3f3f46] shrink-0" style={{ height: 'var(--l4-divider-h)' }} />

            {/* FLIP */}
            <div className="flex-1 flex items-center justify-center gap-2">
                <span className="font-bold tracking-[0.1em] text-[#71717a] uppercase" style={{ fontSize: 'var(--l4-font-8)' }}>Flip</span>
                <span className={`px-1.5 py-[1px] rounded-[3px] font-mono font-black ${ASIAN_WALL_STYLE.flip}`} style={{ fontSize: 'var(--l4-font-12)' }}>
                    {fmtPrice(flipLevel)}
                </span>
            </div>

            <div className="w-[1px] bg-[#3f3f46] shrink-0" style={{ height: 'var(--l4-divider-h)' }} />

            {/* PUT WALL */}
            <div className="flex-1 flex items-center justify-center gap-2">
                <span className="font-bold tracking-[0.1em] text-[#71717a] uppercase whitespace-nowrap" style={{ fontSize: 'var(--l4-font-8)' }}>Put Wall</span>
                <span className={`px-1.5 py-[1px] rounded-[3px] font-mono font-black ${ASIAN_WALL_STYLE.put}`} style={{ fontSize: 'var(--l4-font-12)' }}>
                    {fmtPrice(putWall)}
                </span>
            </div>
        </div>
    )
})

GexStatusBar.displayName = 'GexStatusBar'

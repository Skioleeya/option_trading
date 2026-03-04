/**
 * DepthProfile — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { useEffect, useRef, memo } from 'react'
import { useDashboardStore, selectSpot } from '../../store/dashboardStore'

const selectDepthProfile = (s: ReturnType<typeof useDashboardStore.getState>) =>
    s.payload?.agent_g?.data?.ui_state?.depth_profile ?? null

const selectMacroVolumeMap = (s: ReturnType<typeof useDashboardStore.getState>) =>
    s.payload?.agent_g?.data?.ui_state?.macro_volume_map ?? null

interface PropTableRow {
    strike: number; put_pct: number; call_pct: number
    put_color?: string; call_color?: string
    is_dominant_put: boolean; is_dominant_call: boolean
    is_spot: boolean; is_flip: boolean
    strike_color?: string; put_label_color?: string; call_label_color?: string
    spot_tag_classes?: string; flip_tag_classes?: string
}

interface Props {
    rows?: PropTableRow[]
    macroVolumeMap?: Record<string, number>
    spot?: number | null
}

export const DepthProfile: React.FC<Props> = memo(({ rows: propRows, macroVolumeMap: propMap, spot: propSpot }) => {
    const storeRows = useDashboardStore(selectDepthProfile) as PropTableRow[] | null
    const storeMap = useDashboardStore(selectMacroVolumeMap) as Record<string, number> | null
    const storeSpot = useDashboardStore(selectSpot)

    const rows = storeRows ?? propRows ?? []
    const macroVolumeMap = storeMap ?? propMap ?? {}
    const spot = storeSpot ?? propSpot ?? null

    const safeRows = rows ?? []
    const spotRef = useRef<HTMLDivElement>(null)
    const currentSpot = safeRows.find(r => r.is_spot)?.strike

    useEffect(() => {
        if (spotRef.current) {
            spotRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
    }, [currentSpot])

    const hasMinimap = Object.keys(macroVolumeMap).length > 0
    const maxVol = hasMinimap ? Math.max(...Object.values(macroVolumeMap), 1) : 1
    const sortedStrikes = hasMinimap ? Object.keys(macroVolumeMap).map(Number).sort((a, b) => b - a) : []

    const maxPutPct = safeRows.length > 0 ? Math.max(...safeRows.map(r => r.put_pct), 0) : 0
    const maxCallPct = safeRows.length > 0 ? Math.max(...safeRows.map(r => r.call_pct), 0) : 0

    if (safeRows.length === 0) {
        return <div className="flex flex-1 min-h-0 w-full bg-[#060606] items-center justify-center"><span className="text-[#52525b] text-[10px]">—</span></div>
    }

    return (
        <div className="flex flex-row flex-1 min-h-0 w-full relative bg-[#060606] font-sans selection:bg-transparent overflow-hidden">
            <div className="flex flex-col flex-1 overflow-y-auto relative px-1 py-4 scrollbar-hide" style={{ scrollbarWidth: 'none' }}>
                <div className="flex flex-col w-full relative">
                    {safeRows.map((row) => {
                        const isMaxPut = row.put_pct === maxPutPct && maxPutPct > 0
                        const isMaxCall = row.call_pct === maxCallPct && maxCallPct > 0
                        const hasPut = row.put_pct > 0
                        const hasCall = row.call_pct > 0
                        const isFocusZone = row.is_spot || row.is_flip || isMaxPut || isMaxCall

                        return (
                            <div key={row.strike} ref={row.is_spot ? spotRef : null}
                                className={`relative group w-full h-[24px] flex items-center justify-center transition-colors duration-150 ${isFocusZone ? 'bg-white/[0.03]' : 'hover:bg-white/[0.02]'}`}>
                                {row.is_spot && <div className="absolute left-1/2 -translate-x-1/2 w-full h-full bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#ff3366]/10 via-transparent to-transparent z-0 pointer-events-none"></div>}
                                {row.is_flip && <div className="absolute top-[50%] left-0 w-full h-[1px] border-b border-dashed border-[#fbbf24]/50 z-20 pointer-events-none"></div>}
                                {row.is_spot && <div className="absolute top-[50%] left-0 w-full h-[1px] border-b border-dashed border-[#ff3366]/60 z-20 pointer-events-none shadow-[0_0_8px_rgba(255,51,102,0.6)]"></div>}

                                <div className="flex items-center w-full h-full relative z-10 box-border px-4">
                                    {/* PUT WING */}
                                    <div className="flex-1 h-full flex justify-end items-center relative">
                                        {hasPut && (
                                            <div className={`h-[16px] relative transition-all duration-300 ease-out flex items-center justify-end ${row.is_dominant_put ? 'bg-gradient-to-l from-[#059669] to-[#10b981] border-l border-[#34d399] shadow-[-2px_0_6px_rgba(16,185,129,0.3)]' : 'bg-gradient-to-l from-[#064e3b] to-[#059669]/90 border-l border-[#10b981]/50'}`}
                                                style={{ width: `${maxPutPct > 0 ? Math.max((row.put_pct / maxPutPct) * 95, 1) : 1}%`, borderTopLeftRadius: '2px', borderBottomLeftRadius: '2px' }}>
                                                {isMaxPut && <div className="absolute right-0 top-1/2 -translate-y-1/2 bg-[#022c22]/90 border-l border-[#10b981]/40 text-[#34d399] text-[9px] font-black px-[4px] py-[1px] rounded-[1px] leading-none z-10">P</div>}
                                            </div>
                                        )}
                                    </div>

                                    {/* CENTER SPINE */}
                                    <div className="w-[50px] h-full flex items-center justify-center relative shrink-0 z-20 bg-[#060606]">
                                        {hasPut && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[1px] h-[16px] bg-[#34d399] z-30 shadow-[0_0_4px_rgba(52,211,153,0.8)]"></div>}
                                        <span className={`font-mono text-[13px] tracking-tight transition-colors z-10 ${row.is_spot ? 'text-[#ff3366] font-black bg-[#ff3366]/10 px-1 rounded' : row.is_flip ? 'text-[#fbbf24] font-bold' : (isMaxPut || isMaxCall) ? 'text-[#f4f4f5] font-bold drop-shadow-[0_0_4px_rgba(255,255,255,0.4)]' : 'text-[#71717a]'}`}>
                                            {row.strike.toFixed(0)}
                                        </span>
                                        {hasCall && <div className="absolute right-0 top-1/2 -translate-y-1/2 w-[1px] h-[16px] bg-[#f87171] z-30 shadow-[0_0_4px_rgba(248,113,113,0.8)]"></div>}
                                    </div>

                                    {/* CALL WING */}
                                    <div className="flex-1 h-full flex justify-start items-center relative">
                                        {hasCall && (
                                            <div className={`h-[16px] relative transition-all duration-300 ease-out flex items-center justify-start ${row.is_dominant_call ? 'bg-gradient-to-r from-[#dc2626] to-[#ef4444] border-r border-[#f87171] shadow-[2px_0_6px_rgba(239,68,68,0.3)]' : 'bg-gradient-to-r from-[#7f1d1d] to-[#dc2626]/90 border-r border-[#ef4444]/50'}`}
                                                style={{ width: `${maxCallPct > 0 ? Math.max((row.call_pct / maxCallPct) * 95, 1) : 1}%`, borderTopRightRadius: '2px', borderBottomRightRadius: '2px' }}>
                                                {isMaxCall && <div className="absolute left-0 top-1/2 -translate-y-1/2 bg-[#450a0a]/90 border-r border-[#ef4444]/40 text-[#f87171] text-[9px] font-black px-[4px] py-[1px] rounded-[1px] leading-none z-10">c</div>}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {row.is_flip && <div className="absolute right-1 top-[50%] -translate-y-[120%] z-40 pointer-events-none"><div className="bg-[#1a1505]/95 border border-[#fbbf24]/80 text-[#fbbf24] text-[9px] font-black px-1.5 py-[1px] rounded-[2px] shadow-[0_2px_4px_rgba(0,0,0,0.5)]">FLIP</div></div>}
                                {row.is_spot && <div className="absolute right-1 top-[50%] -translate-y-[120%] z-50 pointer-events-none"><div className="bg-[#1a050a]/95 border border-[#ff3366]/80 text-[#ff3366] text-[10px] font-black px-1.5 py-[1px] rounded-[2px] shadow-[0_2px_4px_rgba(0,0,0,0.5)] flex items-center gap-1"><span>SPOT</span><span className="font-mono">{spot ? spot.toFixed(2) : row.strike.toFixed(2)}</span></div></div>}
                            </div>
                        )
                    })}
                </div>
            </div>

            {hasMinimap && (
                <div className="w-[14px] border-l border-white/[0.04] bg-[#060606] flex flex-col py-4 px-[1px] relative z-40">
                    {sortedStrikes.map(strike => {
                        const vol = macroVolumeMap[strike]
                        const pct = vol / maxVol
                        const isActiveViewport = safeRows.some(r => r.strike === strike)
                        return (
                            <div key={strike} className="w-full flex justify-end h-[3px] my-[1px] relative">
                                <div className={`h-full transition-all duration-300 ${isActiveViewport ? 'bg-[#a1a1aa] shadow-[0_0_5px_rgba(161,161,170,0.4)]' : 'bg-[#27272a]'}`}
                                    style={{ width: `${Math.max(pct * 100, 10)}%`, opacity: pct > 0.1 ? 1 : 0.4 }} />
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
})

DepthProfile.displayName = 'DepthProfile'

/**
 * DepthProfile — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { useEffect, useRef, memo, useState, useCallback } from 'react'
import {
    useDashboardStore,
    selectSpot,
    selectGammaWalls,
    selectFlipLevel,
    selectUiStateDepthProfile,
    selectUiStateMacroVolumeMap,
} from '../../store/dashboardStore'
import {
    resolveNavigationTarget,
    resolveNearestStrike,
    type DepthProfileNavEvent,
} from './depthProfileNav'

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
    gammaWalls?: { call_wall: number | null; put_wall: number | null } | null
    flipLevel?: number | null
    preferProp?: boolean
}

const DepthProfileRow: React.FC<{
    row: PropTableRow;
    maxPutPct: number;
    maxCallPct: number;
    spot: number | null;
    spotRef: React.MutableRefObject<HTMLDivElement | null>;
    registerRowRef: (strike: number, node: HTMLDivElement | null) => void;
    isNavHighlighted: boolean;
}> = memo(({ row, maxPutPct, maxCallPct, spot, spotRef, registerRowRef, isNavHighlighted }) => {
    const isMaxPut = row.put_pct === maxPutPct && maxPutPct > 0
    const isMaxCall = row.call_pct === maxCallPct && maxCallPct > 0
    const hasPut = row.put_pct > 0
    const hasCall = row.call_pct > 0
    const isFocusZone = row.is_spot || row.is_flip || isMaxPut || isMaxCall

    return (
        <div
            ref={(node) => {
                registerRowRef(row.strike, node)
                if (row.is_spot) {
                    spotRef.current = node
                }
            }}
            data-strike={row.strike}
            className={`relative group w-full h-[20px] flex items-center justify-center transition-colors duration-150 ${isFocusZone ? 'bg-white/[0.03]' : 'hover:bg-white/[0.02]'} ${isNavHighlighted ? 'ring-1 ring-[#fbbf24]/80 bg-[#fbbf24]/10' : ''}`}>
            {row.is_spot && <div className="absolute left-1/2 -translate-x-1/2 w-full h-full bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#ff3366]/10 via-transparent to-transparent z-0 pointer-events-none"></div>}
            {row.is_flip && <div className="absolute top-[50%] left-0 w-full h-[1px] border-b border-dashed border-[#fbbf24]/50 z-20 pointer-events-none"></div>}
            {row.is_spot && <div className="absolute top-[50%] left-0 w-full h-[1px] border-b border-dashed border-[#ff3366]/60 z-20 pointer-events-none shadow-[0_0_8px_rgba(255,51,102,0.6)]"></div>}

            <div className="flex items-center w-full h-full relative z-10 box-border px-4">
                {/* PUT WING */}
                <div className="flex-1 h-full flex justify-end items-center relative">
                    {hasPut && (
                        <div className={`h-[12px] relative transition-all duration-300 ease-out flex items-center justify-end ${row.is_dominant_put ? 'bg-gradient-to-l from-[#059669] to-[#10b981] border-l border-[#34d399] shadow-[-2px_0_6px_rgba(16,185,129,0.3)]' : 'bg-gradient-to-l from-[#064e3b] to-[#059669]/90 border-l border-[#10b981]/50'}`}
                            style={{ width: `${maxPutPct > 0 ? Math.max((row.put_pct / maxPutPct) * 95, 1) : 1}%`, borderTopLeftRadius: '2px', borderBottomLeftRadius: '2px' }}>
                            {isMaxPut && <div className="absolute right-0 top-1/2 -translate-y-1/2 bg-[#022c22]/90 border-l border-[#10b981]/40 text-[#34d399] text-[9px] font-black px-[4px] py-[1px] rounded-[1px] leading-none z-10">P</div>}
                        </div>
                    )}
                </div>

                {/* CENTER SPINE */}
                <div className="w-[50px] h-full flex items-center justify-center relative shrink-0 z-20 bg-[#060606]">
                    {hasPut && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[1px] h-[12px] bg-[#34d399] z-30 shadow-[0_0_4px_rgba(52,211,153,0.8)]"></div>}
                    <span className={`font-mono text-[11px] tracking-tight transition-colors z-10 ${row.is_spot ? 'text-[#ff3366] font-black bg-[#ff3366]/10 px-0.5 rounded' : row.is_flip ? 'text-[#fbbf24] font-bold' : (isMaxPut || isMaxCall) ? 'text-[#f4f4f5] font-bold drop-shadow-[0_0_4px_rgba(255,255,255,0.4)]' : 'text-[#71717a]'}`}>
                        {row.strike.toFixed(0)}
                    </span>
                    {hasCall && <div className="absolute right-0 top-1/2 -translate-y-1/2 w-[1px] h-[12px] bg-[#f87171] z-30 shadow-[0_0_4px_rgba(248,113,113,0.8)]"></div>}
                </div>

                {/* CALL WING */}
                <div className="flex-1 h-full flex justify-start items-center relative">
                    {hasCall && (
                        <div className={`h-[12px] relative transition-all duration-300 ease-out flex items-center justify-start ${row.is_dominant_call ? 'bg-gradient-to-r from-[#dc2626] to-[#ef4444] border-r border-[#f87171] shadow-[2px_0_6px_rgba(239,68,68,0.3)]' : 'bg-gradient-to-r from-[#7f1d1d] to-[#dc2626]/90 border-r border-[#ef4444]/50'}`}
                            style={{ width: `${maxCallPct > 0 ? Math.max((row.call_pct / maxCallPct) * 95, 1) : 1}%`, borderTopRightRadius: '2px', borderBottomRightRadius: '2px' }}>
                            {isMaxCall && <div className="absolute left-0 top-1/2 -translate-y-1/2 bg-[#450a0a]/90 border-r border-[#ef4444]/40 text-[#f87171] text-[9px] font-black px-[4px] py-[1px] rounded-[1px] leading-none z-10">c</div>}
                        </div>
                    )}
                </div>
            </div>

            {row.is_flip && <div className="absolute right-1 top-[50%] -translate-y-[50%] z-40 pointer-events-none"><div className="bg-[#1a1505]/95 border border-[#fbbf24]/80 text-[#fbbf24] text-[8px] font-black px-1 py-[0px] rounded-[1px] shadow-[0_2px_4px_rgba(0,0,0,0.5)]">FLIP</div></div>}
            {row.is_spot && <div className="absolute right-1 top-[50%] -translate-y-[50%] z-50 pointer-events-none"><div className="bg-[#1a050a]/95 border border-[#ff3366]/80 text-[#ff3366] text-[9px] font-black px-1 py-[0px] rounded-[1px] shadow-[0_2px_4px_rgba(0,0,0,0.5)] flex items-center gap-1"><span>SPOT</span><span className="font-mono">{spot ? spot.toFixed(1) : row.strike.toFixed(1)}</span></div></div>}
        </div>
    )
}, (prev, next) => {
    // Custom comparison to prevent re-render unless visual values changed
    return (
        prev.row.strike === next.row.strike &&
        prev.row.call_pct === next.row.call_pct &&
        prev.row.put_pct === next.row.put_pct &&
        prev.row.is_spot === next.row.is_spot &&
        prev.row.is_flip === next.row.is_flip &&
        prev.maxPutPct === next.maxPutPct &&
        prev.maxCallPct === next.maxCallPct &&
        prev.spot === next.spot &&
        prev.isNavHighlighted === next.isNavHighlighted
    )
})

DepthProfileRow.displayName = 'DepthProfileRow'

export const DepthProfile: React.FC<Props> = memo(({
    rows: propRows,
    macroVolumeMap: propMap,
    spot: propSpot,
    gammaWalls: propGammaWalls,
    flipLevel: propFlipLevel,
    preferProp = false,
}) => {
    const storeRows = useDashboardStore(selectUiStateDepthProfile) as PropTableRow[] | null
    const storeMap = useDashboardStore(selectUiStateMacroVolumeMap) as Record<string, number> | null
    const storeSpot = useDashboardStore(selectSpot)
    const storeGammaWalls = useDashboardStore(selectGammaWalls)
    const storeFlipLevel = useDashboardStore(selectFlipLevel)

    const rows = preferProp
        ? (propRows ?? storeRows ?? [])
        : (storeRows ?? propRows ?? [])
    const macroVolumeMap = preferProp
        ? (propMap ?? storeMap ?? {})
        : (storeMap ?? propMap ?? {})
    const spot = preferProp
        ? (propSpot ?? storeSpot ?? null)
        : (storeSpot ?? propSpot ?? null)
    const gammaWalls = preferProp
        ? (propGammaWalls ?? storeGammaWalls ?? null)
        : (storeGammaWalls ?? propGammaWalls ?? null)
    const flipLevelRaw = preferProp
        ? (propFlipLevel ?? storeFlipLevel ?? null)
        : (storeFlipLevel ?? propFlipLevel ?? null)

    const safeRows = rows ?? []
    const spotRef = useRef<HTMLDivElement>(null)
    const rowNodeMapRef = useRef<Map<number, HTMLDivElement>>(new Map())
    const navHighlightTimerRef = useRef<number | null>(null)
    const lastManualNavAtRef = useRef(0)
    const [navHighlightStrike, setNavHighlightStrike] = useState<number | null>(null)
    const currentSpot = React.useMemo(() => safeRows.find(r => r.is_spot)?.strike, [safeRows])
    const rowStrikes = React.useMemo(() => safeRows.map((row) => row.strike), [safeRows])
    const callWall = gammaWalls?.call_wall ?? null
    const putWall = gammaWalls?.put_wall ?? null
    const flipLevel = flipLevelRaw

    const registerRowRef = useCallback((strike: number, node: HTMLDivElement | null) => {
        if (node) {
            rowNodeMapRef.current.set(strike, node)
        } else {
            rowNodeMapRef.current.delete(strike)
        }
    }, [])

    const highlightStrike = useCallback((strike: number) => {
        setNavHighlightStrike(strike)
        if (navHighlightTimerRef.current != null) {
            window.clearTimeout(navHighlightTimerRef.current)
        }
        navHighlightTimerRef.current = window.setTimeout(() => {
            setNavHighlightStrike(null)
            navHighlightTimerRef.current = null
        }, 1200)
    }, [])

    const scrollToStrike = useCallback((targetStrike: number | null) => {
        const resolved = resolveNearestStrike(targetStrike, rowStrikes)
        if (resolved == null) {
            return
        }
        const node = rowNodeMapRef.current.get(resolved)
        if (!node) {
            return
        }
        lastManualNavAtRef.current = Date.now()
        node.scrollIntoView({ behavior: 'auto', block: 'center' })
        highlightStrike(resolved)
    }, [highlightStrike, rowStrikes])

    useEffect(() => {
        if (spotRef.current) {
            if (Date.now() - lastManualNavAtRef.current < 1200) {
                return
            }
            // Speed up scroll behavior to prevent 'fighting' with 1Hz updates
            spotRef.current.scrollIntoView({ behavior: 'auto', block: 'center' })
        }
    }, [currentSpot])

    useEffect(() => {
        const events: DepthProfileNavEvent[] = [
            'l4:nav_spot',
            'l4:nav_call_wall',
            'l4:nav_put_wall',
            'l4:nav_flip',
        ]

        const handlers = events.map((eventType) => {
            const handler = () => {
                const target = resolveNavigationTarget({
                    eventType,
                    spot,
                    currentSpotStrike: currentSpot ?? null,
                    callWall,
                    putWall,
                    flipLevel,
                })
                scrollToStrike(target)
            }
            window.addEventListener(eventType, handler)
            return { eventType, handler }
        })

        return () => {
            handlers.forEach(({ eventType, handler }) => {
                window.removeEventListener(eventType, handler)
            })
        }
    }, [callWall, currentSpot, flipLevel, putWall, scrollToStrike, spot])

    useEffect(() => {
        return () => {
            if (navHighlightTimerRef.current != null) {
                window.clearTimeout(navHighlightTimerRef.current)
            }
        }
    }, [])

    const hasMinimap = Object.keys(macroVolumeMap).length > 0
    const { maxVol, sortedStrikes } = React.useMemo(() => {
        if (!hasMinimap) return { maxVol: 1, sortedStrikes: [] }
        const values = Object.values(macroVolumeMap)
        return {
            maxVol: Math.max(...values, 1),
            sortedStrikes: Object.keys(macroVolumeMap).map(Number).sort((a, b) => b - a)
        }
    }, [macroVolumeMap, hasMinimap])

    const { maxPutPct, maxCallPct } = React.useMemo(() => {
        if (safeRows.length === 0) return { maxPutPct: 0, maxCallPct: 0 }
        return {
            maxPutPct: Math.max(...safeRows.map(r => r.put_pct), 0),
            maxCallPct: Math.max(...safeRows.map(r => r.call_pct), 0)
        }
    }, [safeRows])

    if (safeRows.length === 0) {
        return <div className="flex flex-1 min-h-0 w-full bg-[#060606] items-center justify-center"><span className="text-[#52525b] text-[10px]">—</span></div>
    }

    return (
        <div className="flex flex-row flex-1 min-h-0 w-full relative bg-[#060606] font-sans selection:bg-transparent overflow-hidden">
            <div className="flex flex-col flex-1 items-center justify-center overflow-y-auto relative px-1 py-2 scrollbar-hide" style={{ scrollbarWidth: 'none' }}>
                <div className="flex flex-col w-full relative">
                    {safeRows.map((row) => (
                        <DepthProfileRow
                            key={row.strike}
                            row={row}
                            maxPutPct={maxPutPct}
                            maxCallPct={maxCallPct}
                            spot={spot}
                            spotRef={spotRef}
                            registerRowRef={registerRowRef}
                            isNavHighlighted={navHighlightStrike === row.strike}
                        />
                    ))}
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

/**
 * WallMigration — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { fmtPrice } from '../../lib/utils'
import { useDashboardStore, selectUiStateWallMigration } from '../../store/dashboardStore'
import { getHistoryValue, getWallMigrationRowTokens } from './wallMigrationTheme'

interface PropTableRow {
    label: string
    strike: number | null
    state: string
    history: number[]
    lights?: Record<string, string>
}

interface Props {
    rows?: PropTableRow[]
    preferProp?: boolean
}

export const WallMigration: React.FC<Props> = memo(({ rows: propRows, preferProp = false }) => {
    const storeRows = useDashboardStore(selectUiStateWallMigration) as PropTableRow[] | null
    const rows = preferProp
        ? (propRows ?? storeRows ?? [])
        : (storeRows ?? propRows ?? [])

    if (!rows || rows.length === 0) {
        return (
            <div className="p-2 pb-3 flex flex-col gap-1.5 font-sans bg-[#060606] selection:bg-transparent">
                <div className="flex items-center mb-1 px-1">
                    <div className="w-[2px] h-[10px] bg-[#d4d4d8] shadow-[0_0_4px_rgba(212,212,216,0.5)] mr-1.5"></div>
                    <span className="text-[10px] font-black text-[#d4d4d8] tracking-widest leading-none">WALL MIGRATION</span>
                </div>
                <div className="text-[10px] text-[#52525b] px-1">—</div>
            </div>
        )
    }

    return (
        <div className="p-2 pb-3 flex flex-col gap-1.5 font-sans bg-[#060606] selection:bg-transparent">
            <div className="flex items-center mb-1 px-1">
                <div className="w-[2px] h-[10px] bg-[#d4d4d8] shadow-[0_0_4px_rgba(212,212,216,0.5)] mr-1.5"></div>
                <span className="text-[10px] font-black text-[#d4d4d8] tracking-widest leading-none">WALL MIGRATION</span>
            </div>

            {rows.map((row, i) => {
                const tokens = getWallMigrationRowTokens(row)
                const h1 = getHistoryValue(row.history, 0)
                const h2 = getHistoryValue(row.history, 1)

                return (
                    <div key={i} className="flex items-center gap-1 px-1 relative">
                        <div className="w-6 h-[22px] flex items-center justify-center text-[10px] font-black flex-shrink-0 rounded-[2px]"
                            style={{
                                color: tokens.labelColor,
                                border: `1px solid ${tokens.labelBorder}`,
                                backgroundColor: tokens.labelBg,
                            }}>
                            {row.label}
                        </div>

                        <div className="flex-1 flex items-center justify-center h-[22px] bg-[#0a0a0a] border border-white/[0.03] rounded-[2px]">
                            <span className="font-mono text-[11px] font-medium text-[#3f3f46]">
                                {h1 != null && h1 > 0 ? fmtPrice(h1) : '—'}
                            </span>
                        </div>

                        <div className="flex-1 flex items-center justify-center h-[22px] bg-[#0a0a0a] border border-white/[0.06] rounded-[2px]">
                            <span className="font-mono text-[11px] font-medium text-[#71717a]">
                                {h2 != null && h2 > 0 ? fmtPrice(h2) : '—'}
                            </span>
                        </div>

                        <div className="flex-1 flex items-center justify-center h-[22px] relative overflow-hidden rounded-[2px] transition-colors duration-300"
                            style={{
                                border: `1px solid ${tokens.currentBorder}`,
                                backgroundColor: tokens.currentBg,
                                boxShadow: tokens.currentShadow,
                            }}>
                            {tokens.isBreached && <div className="absolute inset-0 shadow-[inset_0_0_8px_rgba(255,255,255,0.3)] pointer-events-none"></div>}
                            {tokens.isReinforced && <div className="absolute inset-0 pointer-events-none" style={{ boxShadow: `inset 0 0 10px ${tokens.isCall ? 'rgba(239,68,68,0.25)' : 'rgba(16,185,129,0.25)'}` }}></div>}
                            {tokens.isRetreating && <div className="absolute left-0 top-0 bottom-0 w-[2px] shadow-[0_0_6px_rgba(234,179,8,0.8)] pointer-events-none" style={{ backgroundColor: tokens.retreatColor }}></div>}

                            <span className={`font-mono text-[12px] relative z-10 ${tokens.isDecaying ? 'text-[#52525b] font-medium' :
                                tokens.isBreached ? 'text-white font-black drop-shadow-[0_0_4px_rgba(255,255,255,0.8)]' :
                                    'text-[#e4e4e7] font-bold'}`}>
                                {row.strike != null && row.strike > 0 ? fmtPrice(row.strike) : '—'}
                            </span>
                        </div>

                        <div className="w-[54px] flex items-center justify-end pl-1 flex-shrink-0">
                            <span className={`text-[9px] font-mono font-bold tracking-wider truncate ${tokens.isBreached ? 'animate-pulse' : ''}`}
                                style={{ color: tokens.badgeColor, textShadow: tokens.isDecaying ? 'none' : `0 0 6px ${tokens.badgeColor}60` }}>
                                {row.lights?.wall_dyn_badge || row.state}
                            </span>
                        </div>
                    </div>
                )
            })}
        </div>
    )
})

WallMigration.displayName = 'WallMigration'

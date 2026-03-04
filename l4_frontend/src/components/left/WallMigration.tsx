/**
 * WallMigration — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { fmtPrice } from '../../lib/utils'
import { useDashboardStore } from '../../store/dashboardStore'

const selectWallMigration = (s: ReturnType<typeof useDashboardStore.getState>) =>
    s.payload?.agent_g?.data?.ui_state?.wall_migration ?? null

interface PropTableRow {
    type_label: string
    type_bg: string
    type_text: string
    h1: number | null
    h2: number | null
    current: number | null
    dot_color: string
    current_border: string
    current_bg: string
    current_shadow: string
    current_text: string
    current_pulse: string
    wall_dyn_badge: string
    wall_dyn_color: string
    state: string
}

interface Props {
    rows?: PropTableRow[]
}

export const WallMigration: React.FC<Props> = memo(({ rows: propRows }) => {
    const storeRows = useDashboardStore(selectWallMigration) as PropTableRow[] | null
    const rows = storeRows ?? propRows ?? []

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
                const isCall = row.type_label === 'C'
                const baseColor = isCall ? '#ef4444' : '#10b981'
                const baseBorder = isCall ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'
                const baseBg = isCall ? 'rgba(69,10,10,0.5)' : 'rgba(2,44,34,0.5)'
                const isBreached = row.state.includes('BREACHED')
                const isDecaying = row.state.includes('DECAYING')
                const isReinforced = row.state.includes('REINFORCED')
                const isRetreating = row.state.includes('RETREATING')
                const badgeColor = row.wall_dyn_color || '#a1a1aa'

                return (
                    <div key={i} className="flex items-center gap-1 px-1 relative">
                        <div className="w-6 h-[22px] flex items-center justify-center text-[10px] font-black flex-shrink-0 rounded-[2px]"
                            style={{ color: baseColor, border: `1px solid ${baseBorder}`, backgroundColor: baseBg }}>
                            {row.type_label}
                        </div>

                        <div className="flex-1 flex items-center justify-center h-[22px] bg-[#0a0a0a] border border-white/[0.03] rounded-[2px]">
                            <span className="font-mono text-[11px] font-medium text-[#3f3f46]">
                                {row.h1 != null ? fmtPrice(row.h1) : '—'}
                            </span>
                        </div>

                        <div className="flex-1 flex items-center justify-center h-[22px] bg-[#0a0a0a] border border-white/[0.06] rounded-[2px]">
                            <span className="font-mono text-[11px] font-medium text-[#71717a]">
                                {row.h2 != null ? fmtPrice(row.h2) : '—'}
                            </span>
                        </div>

                        <div className="flex-1 flex items-center justify-center h-[22px] relative overflow-hidden rounded-[2px] transition-colors duration-300"
                            style={{
                                border: `1px solid ${row.current_border || 'rgba(255,255,255,0.1)'}`,
                                backgroundColor: isDecaying ? '#060606' : 'rgba(18,18,20,0.8)',
                            }}>
                            {isBreached && <div className="absolute inset-0 shadow-[inset_0_0_8px_rgba(255,255,255,0.3)] pointer-events-none"></div>}
                            {isReinforced && <div className="absolute inset-0 pointer-events-none" style={{ boxShadow: `inset 0 0 10px ${isCall ? 'rgba(239,68,68,0.25)' : 'rgba(16,185,129,0.25)'}` }}></div>}
                            {isRetreating && <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-[#eab308] shadow-[0_0_6px_rgba(234,179,8,0.8)] pointer-events-none"></div>}

                            <span className={`font-mono text-[12px] relative z-10 ${isDecaying ? 'text-[#52525b] font-medium' :
                                isBreached ? 'text-white font-black drop-shadow-[0_0_4px_rgba(255,255,255,0.8)]' :
                                    'text-[#e4e4e7] font-bold'}`}>
                                {row.current != null ? fmtPrice(row.current) : '—'}
                            </span>
                        </div>

                        <div className="w-[54px] flex items-center justify-end pl-1 flex-shrink-0">
                            <span className={`text-[9px] font-mono font-bold tracking-wider truncate ${isBreached ? 'animate-pulse' : ''}`}
                                style={{ color: badgeColor, textShadow: isDecaying ? 'none' : `0 0 6px ${badgeColor}60` }}>
                                {row.wall_dyn_badge}
                            </span>
                        </div>
                    </div>
                )
            })}
        </div>
    )
})

WallMigration.displayName = 'WallMigration'

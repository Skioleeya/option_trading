/**
 * WallMigration — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { useDashboardStore, selectUiStateWallMigration } from '../../store/dashboardStore'
import { getHistoryValue, getWallMigrationRowTokens, isDisplayableWallLevel } from './wallMigrationTheme'
import { buildWallMigrationGridTemplate, formatWallMigrationStrike } from './wallMigrationLayout'

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
            <div className="flex flex-col font-sans bg-[#060606] selection:bg-transparent" style={{ padding: 'var(--l4-panel-pad)', gap: 'var(--l4-panel-gap)' }}>
                <div className="flex items-center mb-1 px-1">
                    <div className="bg-[#d4d4d8] shadow-[0_0_4px_rgba(212,212,216,0.5)] mr-1.5" style={{ width: 'var(--l4-row-accent-w)', height: 'var(--l4-font-10)' }}></div>
                    <span className="font-black text-[#d4d4d8] tracking-widest leading-none" style={{ fontSize: 'var(--l4-font-10)' }}>WALL MIGRATION</span>
                </div>
                <div className="text-[#52525b] px-1" style={{ fontSize: 'var(--l4-font-10)' }}>—</div>
            </div>
        )
    }

    return (
        <div className="flex flex-col font-sans bg-[#060606] selection:bg-transparent" style={{ padding: 'var(--l4-panel-pad)', gap: 'var(--l4-panel-gap)' }}>
            <div className="flex items-center mb-1 px-1">
                <div className="bg-[#d4d4d8] shadow-[0_0_4px_rgba(212,212,216,0.5)] mr-1.5" style={{ width: 'var(--l4-row-accent-w)', height: 'var(--l4-font-10)' }}></div>
                <span className="font-black text-[#d4d4d8] tracking-widest leading-none" style={{ fontSize: 'var(--l4-font-10)' }}>WALL MIGRATION</span>
            </div>

            {rows.map((row, i) => {
                const tokens = getWallMigrationRowTokens(row)
                const h1 = getHistoryValue(row.history, 0)
                const h2 = getHistoryValue(row.history, 1)
                const h1Text = isDisplayableWallLevel(h1) ? formatWallMigrationStrike(h1) : '—'
                const h2Text = isDisplayableWallLevel(h2) ? formatWallMigrationStrike(h2) : '—'
                const currentText = isDisplayableWallLevel(row.strike) ? formatWallMigrationStrike(row.strike) : '—'
                const rowGridTemplate = buildWallMigrationGridTemplate()

                return (
                    <div
                        key={i}
                        className="grid items-center gap-1 px-1 relative min-w-0"
                        style={{ gridTemplateColumns: rowGridTemplate }}
                    >
                        <div className="flex items-center justify-center font-black flex-shrink-0 rounded-[2px]"
                            style={{
                                height: 'var(--l4-wall-row-h)',
                                fontSize: 'var(--l4-font-10)',
                                color: tokens.labelColor,
                                border: `1px solid ${tokens.labelBorder}`,
                                backgroundColor: tokens.labelBg,
                            }}>
                            {row.label}
                        </div>

                        <div
                            className="min-w-0 flex items-center justify-center bg-[#0a0a0a] border border-white/[0.03] rounded-[2px]"
                            style={{ height: 'var(--l4-wall-row-h)' }}
                        >
                            <span className="font-mono font-medium text-[#3f3f46] whitespace-nowrap overflow-hidden text-ellipsis" style={{ fontSize: 'var(--l4-font-11)' }}>
                                {h1Text}
                            </span>
                        </div>

                        <div
                            className="min-w-0 flex items-center justify-center bg-[#0a0a0a] border border-white/[0.06] rounded-[2px]"
                            style={{ height: 'var(--l4-wall-row-h)' }}
                        >
                            <span className="font-mono font-medium text-[#71717a] whitespace-nowrap overflow-hidden text-ellipsis" style={{ fontSize: 'var(--l4-font-11)' }}>
                                {h2Text}
                            </span>
                        </div>

                        <div className="min-w-0 flex items-center justify-center relative overflow-hidden rounded-[2px]"
                            style={{
                                height: 'var(--l4-wall-row-h)',
                                border: `1px solid ${tokens.currentBorder}`,
                                backgroundColor: tokens.currentBg,
                                boxShadow: tokens.currentShadow,
                            }}>
                            {(tokens.isBreached || tokens.isCollapsing) && <div className="absolute inset-0 shadow-[inset_0_0_8px_rgba(255,255,255,0.3)] pointer-events-none"></div>}
                            {tokens.isReinforced && <div className="absolute inset-0 pointer-events-none" style={{ boxShadow: `inset 0 0 10px ${tokens.badgeColor}40` }}></div>}
                            {tokens.isRetreating && <div className="absolute left-0 top-0 bottom-0 shadow-[0_0_6px_rgba(234,179,8,0.8)] pointer-events-none" style={{ width: 'var(--l4-row-accent-w)', backgroundColor: tokens.retreatColor }}></div>}

                            <span className={`font-mono relative z-10 ${tokens.isDecaying ? 'text-[#52525b] font-medium' :
                                (tokens.isBreached || tokens.isCollapsing) ? 'text-white font-black drop-shadow-[0_0_4px_rgba(255,255,255,0.8)]' :
                                    'text-[#e4e4e7] font-bold'} whitespace-nowrap`} style={{ fontSize: 'var(--l4-font-12)' }}>
                                {currentText}
                            </span>
                        </div>

                        <div className="min-w-0 flex items-center justify-end pl-1">
                            <span className="font-mono font-bold tracking-wider truncate"
                                style={{
                                    fontSize: 'var(--l4-font-9)',
                                    color: tokens.badgeColor,
                                    textShadow: tokens.isDecaying ? 'none' : `0 0 6px ${tokens.badgeColor}60`,
                                }}>
                                {row.lights?.wall_dyn_badge || tokens.state}
                            </span>
                        </div>
                    </div>
                )
            })}
        </div>
    )
})

WallMigration.displayName = 'WallMigration'

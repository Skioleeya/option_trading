/**
 * AtmDecayOverlay — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import type { AtmDecay } from '../../types/dashboard'
import { fmtPct, fmtPrice } from '../../lib/utils'
import { LineChart } from 'lucide-react'
import { useDashboardStore, selectAtm, selectAtmHistory } from '../../store/dashboardStore'
import { resolveDisplayAtm } from './atmDecayDisplay'
import { THEME } from '../../lib/theme'

interface Props {
    atm?: AtmDecay | null
    spot?: number | null
    history?: AtmDecay[]
}

export const AtmDecayOverlay: React.FC<Props> = memo(({ atm: propAtm, history: propHistory }) => {
    const storeAtm = useDashboardStore(selectAtm) as AtmDecay | null
    const storeHistory = useDashboardStore(selectAtmHistory) as AtmDecay[]
    const atm = resolveDisplayAtm(
        storeAtm ?? propAtm ?? null,
        storeHistory.length > 0 ? storeHistory : (propHistory ?? [])
    )

    const baseLockPrice = atm?.base_strike ?? atm?.strike ?? null
    const currentStrike = atm?.strike ?? null
    const lockedTime = atm?.locked_at ?? null
    const isDynamic = currentStrike !== null && baseLockPrice !== null && currentStrike !== baseLockPrice

    return (
        <div className="absolute top-4 left-4 bg-[#121214]/95 border border-[#27272a] rounded-xl p-3 shadow-2xl z-10 font-sans pointer-events-none w-max">
            <div className="flex items-center gap-1.5 mb-2.5">
                <LineChart size={12} className="text-[#71717a]" />
                <span className="text-[10px] font-bold tracking-widest text-[#71717a] uppercase">SPY 0DTE ATM DECAY</span>
            </div>

            <div className="flex flex-col gap-0.5 mb-4">
                <div className="flex items-baseline gap-1.5">
                    <span className="text-[12px] font-black text-[#e4e4e7]">
                        OPENING ATM {baseLockPrice != null ? fmtPrice(baseLockPrice) : <span className="text-[#52525b]">-- PENDING</span>}
                    </span>
                    <span className="text-[10px] font-medium text-[#52525b] uppercase">
                        {lockedTime ? `(LOCKED ${lockedTime} ET)` : '(AWAITING LOCK)'}
                    </span>
                </div>
                {isDynamic && (
                    <div className="flex items-baseline gap-1.5 mt-0.5">
                        <span className="text-[10px] font-bold text-[#8b5cf6]">
                            ACTIVE ANCHOR {fmtPrice(currentStrike)}
                        </span>
                        <span className="text-[9px] font-medium text-[#7c3aed] uppercase">
                            (SCM STITCHED)
                        </span>
                    </div>
                )}
            </div>

            <div className="flex items-center gap-2.5">
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-[#3f3f46]">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: THEME.accent.amber }} />
                    <span className="text-[9px] font-black text-[#a1a1aa] tracking-widest">STRADDLE</span>
                    <span className="font-mono text-[11px] font-bold" style={{ color: THEME.accent.amber }}>{fmtPct(atm?.straddle_pct)}</span>
                </div>

                <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-[#3f3f46]">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: THEME.market.up }} />
                    <span className="text-[9px] font-black text-[#a1a1aa] tracking-widest">CALL</span>
                    <span className="font-mono text-[11px] font-bold" style={{ color: THEME.market.up }}>{fmtPct(atm?.call_pct)}</span>
                </div>

                <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-[#3f3f46]">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: THEME.market.down }} />
                    <span className="text-[9px] font-black text-[#a1a1aa] tracking-widest">PUT</span>
                    <span className="font-mono text-[11px] font-bold" style={{ color: THEME.market.down }}>{fmtPct(atm?.put_pct)}</span>
                </div>
            </div>
        </div>
    )
})

AtmDecayOverlay.displayName = 'AtmDecayOverlay'

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
        <div
            className="bg-[#121214]/95 border border-[#27272a] shadow-2xl z-10 font-sans pointer-events-none w-max"
            style={{ borderRadius: 'var(--l4-radius-xl)', padding: 'var(--l4-overlay-card-pad)' }}
        >
            <div className="flex items-center gap-1.5 mb-2">
                <LineChart size={12} className="text-[#71717a]" style={{ width: 'var(--l4-icon-sm)', height: 'var(--l4-icon-sm)' }} />
                <span className="font-bold tracking-widest text-[#71717a] uppercase" style={{ fontSize: 'var(--l4-font-10)' }}>SPY 0DTE ATM DECAY</span>
            </div>

            <div className="flex flex-col gap-0.5 mb-3">
                <div className="flex items-baseline gap-1.5">
                    <span className="font-black text-[#e4e4e7]" style={{ fontSize: 'var(--l4-font-12)' }}>
                        OPENING ATM {baseLockPrice != null ? fmtPrice(baseLockPrice) : <span className="text-[#52525b]">-- PENDING</span>}
                    </span>
                    <span className="font-medium text-[#52525b] uppercase" style={{ fontSize: 'var(--l4-font-10)' }}>
                        {lockedTime ? `(LOCKED ${lockedTime} ET)` : '(AWAITING LOCK)'}
                    </span>
                </div>
                {isDynamic && (
                    <div className="flex items-baseline gap-1.5 mt-0.5">
                        <span className="font-bold text-[#8b5cf6]" style={{ fontSize: 'var(--l4-font-10)' }}>
                            ACTIVE ANCHOR {fmtPrice(currentStrike)}
                        </span>
                        <span className="font-medium text-[#7c3aed] uppercase" style={{ fontSize: 'var(--l4-font-9)' }}>
                            (SCM STITCHED)
                        </span>
                    </div>
                )}
            </div>

            <div className="flex items-center flex-wrap" style={{ gap: 'var(--l4-panel-gap)' }}>
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-[#3f3f46]">
                    <span className="rounded-full" style={{ width: 'var(--l4-dot-sm)', height: 'var(--l4-dot-sm)', backgroundColor: THEME.accent.amber }} />
                    <span className="font-black text-[#a1a1aa] tracking-widest" style={{ fontSize: 'var(--l4-font-9)' }}>STRADDLE</span>
                    <span className="font-mono font-bold" style={{ color: THEME.accent.amber, fontSize: 'var(--l4-font-11)' }}>{fmtPct(atm?.straddle_pct)}</span>
                </div>

                <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-[#3f3f46]">
                    <span className="rounded-full" style={{ width: 'var(--l4-dot-sm)', height: 'var(--l4-dot-sm)', backgroundColor: THEME.market.up }} />
                    <span className="font-black text-[#a1a1aa] tracking-widest" style={{ fontSize: 'var(--l4-font-9)' }}>CALL</span>
                    <span className="font-mono font-bold" style={{ color: THEME.market.up, fontSize: 'var(--l4-font-11)' }}>{fmtPct(atm?.call_pct)}</span>
                </div>

                <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-[#3f3f46]">
                    <span className="rounded-full" style={{ width: 'var(--l4-dot-sm)', height: 'var(--l4-dot-sm)', backgroundColor: THEME.market.down }} />
                    <span className="font-black text-[#a1a1aa] tracking-widest" style={{ fontSize: 'var(--l4-font-9)' }}>PUT</span>
                    <span className="font-mono font-bold" style={{ color: THEME.market.down, fontSize: 'var(--l4-font-11)' }}>{fmtPct(atm?.put_pct)}</span>
                </div>
            </div>
        </div>
    )
})

AtmDecayOverlay.displayName = 'AtmDecayOverlay'

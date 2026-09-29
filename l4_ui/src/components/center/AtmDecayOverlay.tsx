/**
 * AtmDecayOverlay — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: ENLARGED
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
            className="bg-[#121214]/95 border border-[#27272a] shadow-2xl z-10 font-sans pointer-events-none"
            style={{ borderRadius: 'var(--l4-radius-xl)', padding: '12px 14px', width: '290px' }}
        >
            {/* Header with Title and Opening ATM */}
            <div className="mb-3 pb-2.5 border-b border-[#27272a]/50">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-1.5">
                        <LineChart size={10} className="text-[#71717a]" style={{ width: '10px', height: '10px' }} />
                        <span className="font-bold tracking-wider text-[#71717a] uppercase" style={{ fontSize: '9px', letterSpacing: '0.1em' }}>SPY 0DTE ATM DECAY</span>
                    </div>
                </div>
                <div className="flex items-baseline justify-between">
                    <span className="font-medium text-[#71717a] uppercase" style={{ fontSize: '8px', letterSpacing: '0.08em' }}>OPENING ATM</span>
                    <span className="font-bold text-[#a1a1aa]" style={{ fontSize: '11px' }}>
                        {baseLockPrice != null ? fmtPrice(baseLockPrice) : <span className="text-[#52525b]">--</span>}
                    </span>
                    <span className="font-medium text-[#52525b]" style={{ fontSize: '7px' }}>
                        {lockedTime ? lockedTime : '--'}
                    </span>
                </div>
                {isDynamic && (
                    <div className="mt-1.5 flex items-baseline justify-between text-[#8b5cf6]">
                        <span className="font-medium uppercase" style={{ fontSize: '7px', letterSpacing: '0.08em' }}>ANCHOR</span>
                        <span className="font-bold" style={{ fontSize: '10px' }}>{fmtPrice(currentStrike)}</span>
                        <span className="font-medium text-[#7c3aed]" style={{ fontSize: '6px' }}>SCM</span>
                    </div>
                )}
            </div>

            {/* Main Metrics - Emphasized */}
            <div className="flex flex-col" style={{ gap: '8px' }}>
                <div className="flex items-center justify-between px-3.5 py-3 rounded-lg bg-gradient-to-r from-[#18181b]/40 to-[#18181b]/20 border border-[#f59e0b]/30 hover:border-[#f59e0b]/50 transition-all shadow-sm">
                    <div className="flex items-center gap-2.5">
                        <span className="rounded-full flex-shrink-0" style={{ width: '9px', height: '9px', backgroundColor: THEME.accent.amber, boxShadow: `0 0 10px ${THEME.accent.amber}60` }} />
                        <span className="font-black text-[#d4d4d8] uppercase tracking-wider" style={{ fontSize: '10px', letterSpacing: '0.12em' }}>STRADDLE</span>
                    </div>
                    <span className="font-mono font-black" style={{ color: THEME.accent.amber, fontSize: '18px', letterSpacing: '-0.02em', textShadow: `0 0 8px ${THEME.accent.amber}40` }}>{fmtPct(atm?.straddle_pct)}</span>
                </div>

                <div className="flex items-center justify-between px-3.5 py-3 rounded-lg bg-gradient-to-r from-[#18181b]/40 to-[#18181b]/20 border border-[#ef4444]/30 hover:border-[#ef4444]/50 transition-all shadow-sm">
                    <div className="flex items-center gap-2.5">
                        <span className="rounded-full flex-shrink-0" style={{ width: '9px', height: '9px', backgroundColor: THEME.market.up, boxShadow: `0 0 10px ${THEME.market.up}60` }} />
                        <span className="font-black text-[#d4d4d8] uppercase tracking-wider" style={{ fontSize: '10px', letterSpacing: '0.12em' }}>CALL</span>
                    </div>
                    <span className="font-mono font-black" style={{ color: THEME.market.up, fontSize: '18px', letterSpacing: '-0.02em', textShadow: `0 0 8px ${THEME.market.up}40` }}>{fmtPct(atm?.call_pct)}</span>
                </div>

                <div className="flex items-center justify-between px-3.5 py-3 rounded-lg bg-gradient-to-r from-[#18181b]/40 to-[#18181b]/20 border border-[#10b981]/30 hover:border-[#10b981]/50 transition-all shadow-sm">
                    <div className="flex items-center gap-2.5">
                        <span className="rounded-full flex-shrink-0" style={{ width: '9px', height: '9px', backgroundColor: THEME.market.down, boxShadow: `0 0 10px ${THEME.market.down}60` }} />
                        <span className="font-black text-[#d4d4d8] uppercase tracking-wider" style={{ fontSize: '10px', letterSpacing: '0.12em' }}>PUT</span>
                    </div>
                    <span className="font-mono font-black" style={{ color: THEME.market.down, fontSize: '18px', letterSpacing: '-0.02em', textShadow: `0 0 8px ${THEME.market.down}40` }}>{fmtPct(atm?.put_pct)}</span>
                </div>
            </div>
        </div>
    )
})

AtmDecayOverlay.displayName = 'AtmDecayOverlay'

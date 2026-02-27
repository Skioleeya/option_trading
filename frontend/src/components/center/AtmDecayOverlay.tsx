import React from 'react'
import type { AtmDecay } from '../../types/dashboard'
import { fmtPct, fmtPrice } from '../../lib/utils'
import { LineChart } from 'lucide-react'

interface Props {
    atm: AtmDecay | null;
    spot: number | null;
    history: AtmDecay[];
}

export const AtmDecayOverlay: React.FC<Props> = ({ atm, spot }) => {
    const lockPrice = atm?.strike ?? spot
    const lockedTime = atm?.locked_at ?? '9:30:00 AM'

    return (
        <div className="absolute top-4 left-4 bg-[#121214]/95 border border-[#27272a] rounded-xl p-3 shadow-2xl z-10 font-sans pointer-events-none w-max">

            {/* Top Header Row */}
            <div className="flex items-center gap-1.5 mb-2.5">
                <LineChart size={12} className="text-[#71717a]" />
                <span className="text-[10px] font-bold tracking-widest text-[#71717a] uppercase">SPY 0DTE ATM DECAY</span>
            </div>

            {/* Sub Header */}
            <div className="flex items-baseline gap-1.5 mb-4">
                <span className="text-[12px] font-black text-[#e4e4e7]">OPENING ATM {fmtPrice(lockPrice)}</span>
                <span className="text-[10px] font-medium text-[#52525b] uppercase">(LOCKED {lockedTime} ET)</span>
            </div>

            {/* Readout Pills Row */}
            <div className="flex items-center gap-2.5">
                {/* STRADDLE */}
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-[#3f3f46]">
                    <span className="w-2 h-2 rounded-full bg-[#f59e0b]" />
                    <span className="text-[9px] font-black text-[#a1a1aa] tracking-widest">STRADDLE</span>
                    <span className="font-mono text-[11px] font-bold text-[#f59e0b]">{fmtPct(atm?.straddle_pct)}</span>
                </div>

                {/* CALL */}
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-[#3f3f46]">
                    <span className="w-2 h-2 rounded-full bg-[#ef4444]" />
                    <span className="text-[9px] font-black text-[#a1a1aa] tracking-widest">CALL</span>
                    <span className="font-mono text-[11px] font-bold text-[#ef4444]">{fmtPct(atm?.call_pct)}</span>
                </div>

                {/* PUT */}
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-[#3f3f46]">
                    <span className="w-2 h-2 rounded-full bg-[#10b981]" />
                    <span className="text-[9px] font-black text-[#a1a1aa] tracking-widest">PUT</span>
                    <span className="font-mono text-[11px] font-bold text-[#10b981]">{fmtPct(atm?.put_pct)}</span>
                </div>
            </div>
        </div>
    )
}
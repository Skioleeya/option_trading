import React from 'react'
import type { AtmDecay } from '../../types/dashboard'
import { fmtPct, fmtPrice } from '../../lib/utils'

interface Props {
    atm: AtmDecay | null
    spot: number | null
}

export const AtmDecayOverlay: React.FC<Props> = ({ atm, spot }) => {
    const lockPrice = atm?.atm_strike ?? spot

    return (
        <div className="glass rounded p-2 text-2xs mono" style={{ minWidth: '200px' }}>
            {/* Lock line */}
            <div className="flex items-center gap-1 mb-1.5">
                <span className="w-2 h-2 rounded-full bg-accent-amber dot-live flex-shrink-0" />
                <span className="text-text-secondary">
                    SPY 0DTE ATM DECAY
                </span>
            </div>

            <div className="text-text-secondary text-2xs mb-1.5">
                OPENING ATM {fmtPrice(lockPrice)}{' '}
                <span className="text-text-muted">(LOCKED 9:30:00 AM ET)</span>
            </div>

            {/* Straddle / Call / Put */}
            <div className="flex items-center gap-3">
                <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-accent-amber flex-shrink-0" />
                    <span className="text-text-secondary">STRADDLE</span>
                    <span className={`font-bold ml-0.5 ${(atm?.straddle_pct ?? 0) < 0 ? 'text-accent-red' : 'text-accent-green'}`}>
                        {fmtPct(atm?.straddle_pct)}
                    </span>
                </div>
            </div>

            <div className="flex items-center gap-4 mt-1">
                <div className="flex items-center gap-1">
                    <span className="text-accent-red font-bold">●</span>
                    <span className="text-text-secondary">CALL</span>
                    <span className={`font-bold ml-0.5 ${(atm?.call_pct ?? 0) < 0 ? 'text-accent-red' : 'text-accent-green'}`}>
                        {fmtPct(atm?.call_pct)}
                    </span>
                </div>

                <div className="flex items-center gap-1">
                    <span className="text-accent-green font-bold">●</span>
                    <span className="text-text-secondary">PUT</span>
                    <span className={`font-bold ml-0.5 ${(atm?.put_pct ?? 0) < 0 ? 'text-accent-red' : 'text-accent-green'}`}>
                        {fmtPct(atm?.put_pct)}
                    </span>
                </div>
            </div>
        </div>
    )
}

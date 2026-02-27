import React from 'react'
import { fmtPrice } from '../../lib/utils'
import type { ConnectionStatus } from '../../types/dashboard'

interface Props {
    spot: number | null
    ivPct: number | null
    ivRegime: string
    status: ConnectionStatus
    marketStatus: string
    as_of: string | null
}

export const Header: React.FC<Props> = ({
    spot, ivPct, ivRegime, status, marketStatus, as_of
}) => {
    const timeStr = as_of
        ? new Date(as_of).toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZone: 'America/New_York',
        })
        : '--:--:--'

    const connColor =
        status === 'connected' ? 'bg-accent-green' :
            status === 'connecting' ? 'bg-accent-amber' :
                'bg-accent-red'

    const ivRegimeColor =
        ivRegime === 'LOW' ? 'text-accent-green' :
            ivRegime === 'NORMAL' ? 'text-accent-green' :
                ivRegime === 'ELEVATED' ? 'text-accent-amber' :
                    ivRegime === 'HIGH' ? 'text-accent-red' :
                        ivRegime === 'EXTREME' ? 'text-accent-red' :
                            'text-text-secondary'

    return (
        <header className="flex items-center justify-between px-3 py-1 border-b border-bg-border bg-bg-secondary"
            style={{ height: '32px' }}>
            {/* Left: Title */}
            <div className="flex items-center gap-3">
                <span className="font-bold tracking-widest text-xs text-text-primary" style={{ letterSpacing: '0.2em' }}>
                    SPX SENTINEL
                </span>
                <span className="mono text-xs text-text-secondary">{timeStr}</span>
            </div>

            {/* Center: Market data pills */}
            <div className="flex items-center gap-2">
                {/* Market Open/Close */}
                <span className={`badge ${marketStatus === 'OPEN' ? 'badge-green' : 'badge-neutral'}`}>
                    {marketStatus}
                </span>

                {/* Spot */}
                <div className="flex items-center gap-1">
                    <span className="section-header">SPY</span>
                    <span className="mono text-sm font-bold text-text-primary">{fmtPrice(spot)}</span>
                </div>

                {/* IV */}
                <div className="flex items-center gap-1">
                    <span className="section-header">IV</span>
                    <span className={`mono text-xs font-bold ${ivRegimeColor}`}>
                        {ivPct != null ? `${ivPct.toFixed(2)}%` : '—'}
                    </span>
                </div>

                {/* IV Regime badge */}
                <span className={`badge ${ivRegime === 'NORMAL' ? 'badge-green' :
                        ivRegime === 'ELEVATED' ? 'badge-amber' :
                            ivRegime === 'HIGH' || ivRegime === 'EXTREME' ? 'badge-red' :
                                'badge-neutral'
                    }`}>{ivRegime || 'NORMAL'}</span>
            </div>

            {/* Right: Connection dots */}
            <div className="flex items-center gap-2">
                <span className="section-header">RDS</span>
                <div className={`w-1.5 h-1.5 rounded-full dot-live ${connColor}`} />
                <span className="section-header">9INS</span>
                <div className={`w-1.5 h-1.5 rounded-full ${connColor}`} />
                <span className="section-header mono text-2xs">LIVE</span>
                <div className="w-1.5 h-1.5 rounded-full bg-accent-green dot-live" />
            </div>
        </header>
    )
}

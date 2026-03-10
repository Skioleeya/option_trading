/**
 * Header — Phase 3: Zustand field-level selectors
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { fmtPrice } from '../../lib/utils'
import type { ConnectionStatus } from '../../types/dashboard'
import { Zap } from 'lucide-react'
import {
    useDashboardStore,
    selectSpot,
    selectIvPct,
    selectConnectionStatus,
    selectPayloadTimestamp,
    selectFusedIvRegime,
    selectUiStateIvVelocity,
    selectRustActive,
} from '../../store/dashboardStore'
import {
    deriveMarketStatus,
    getConnectionDotClass,
    getConnectionLabel,
    getRustIndicator,
} from './headerState'

interface Props {
    spot?: number | null
    ivPct?: number | null
    ivRegime?: string
    status?: ConnectionStatus
    marketStatus?: string
    as_of?: string | null
}

export const Header: React.FC<Props> = memo(({
    spot: propSpot,
    ivPct: propIvPct,
    ivRegime: propIvRegime,
    status: propStatus,
    marketStatus: propMarketStatus,
    as_of: propAsOf,
}) => {
    // Field-level selectors
    const storeSpot = useDashboardStore(selectSpot)
    const storeIvPct = useDashboardStore(selectIvPct)
    const storeStatus = useDashboardStore(selectConnectionStatus)
    const timestamp = useDashboardStore(selectPayloadTimestamp)
    const ivRegimeRaw = useDashboardStore(selectFusedIvRegime)
    const storeIvVelocity = useDashboardStore(selectUiStateIvVelocity)

    const spot = storeSpot ?? propSpot ?? null
    const ivPct = storeIvPct ?? propIvPct ?? null
    const status = storeStatus ?? propStatus ?? 'connecting'
    const as_of = timestamp ?? propAsOf ?? null
    const ivRegime = ivRegimeRaw ?? propIvRegime ?? 'NORMAL'
    const marketStatus = propMarketStatus ?? deriveMarketStatus()
    const rustActive = useDashboardStore(selectRustActive)

    const timeStr = as_of
        ? new Date(as_of).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'America/New_York' })
        : '--:--:--'

    const connColor = getConnectionDotClass(status)
    const connLabel = getConnectionLabel(status)
    const rust = getRustIndicator(rustActive)
    const ivRegimeColor = (ivRegime === 'HIGH' || ivRegime === 'EXTREME') ? 'text-[#ef4444]' : ivRegime === 'ELEVATED' ? 'text-[#f59e0b]' : 'text-[#10b981]'
    const ivBadgeCls = (ivRegime === 'HIGH' || ivRegime === 'EXTREME') ? 'border-[#7f1d1d] text-[#ef4444] bg-[#450a0a]/50' : ivRegime === 'ELEVATED' ? 'border-[#92400e] text-[#f59e0b] bg-[#422006]/50' : 'border-[#065f46] text-[#10b981] bg-[#022c22]/50'

    return (
        <header className="grid items-center h-[36px] border-b border-[#27272a] bg-[#060606] w-full font-sans selection:bg-transparent"
            style={{ gridTemplateColumns: '280px 1fr 320px' }}>

            <div className="flex items-center gap-2 px-3 border-r border-[#27272a] h-full">
                <span className="text-[11px] font-black tracking-[0.2em] text-white/90 uppercase">ANALYSIS</span>
            </div>

            <div className="flex items-center justify-center gap-5 h-full">
                <span className="font-black tracking-[0.15em] text-[#e4e4e7] text-[11px]">SPX SENTINEL</span>
                <div className="w-[1px] h-[12px] bg-[#3f3f46]" />
                <span className="font-mono text-[10px] text-[#71717a]">{timeStr} ET</span>
                <div className="w-[1px] h-[12px] bg-[#3f3f46]" />
                <span className={`text-[10px] font-black tracking-wider ${marketStatus === 'OPEN' ? 'text-[#10b981]' : 'text-[#52525b]'}`}>{marketStatus}</span>
                <div className="w-[1px] h-[12px] bg-[#3f3f46]" />
                <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-bold text-[#71717a]">SPY</span>
                    <span className="font-mono text-[12px] font-black text-[#e4e4e7]">{fmtPrice(spot)}</span>
                </div>
                <div className="w-[1px] h-[12px] bg-[#3f3f46]" />
                <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-bold text-[#71717a]">IV</span>
                    <span className={`font-mono text-[12px] font-black ${ivRegimeColor}`}>{ivPct != null ? `${(ivPct * 100).toFixed(2)}%` : '—'}</span>
                    <span className={`text-[9px] font-black tracking-widest px-1.5 py-[1px] rounded-[2px] border flex flex-col items-center justify-center ${ivBadgeCls}`}>
                        <div className="flex items-center gap-1">
                            {ivRegime}
                            {/* IV Velocity Micro Indicator */}
                            {storeIvVelocity && storeIvVelocity.state && typeof storeIvVelocity.state === 'string' && (
                                <span className={`text-[7px] font-mono whitespace-nowrap ml-1 ${storeIvVelocity.state.includes('EXPANSION') || storeIvVelocity.state.includes('MOVE') ? 'text-[#ef4444] animate-pulse' : storeIvVelocity.state.includes('DROP') ? 'text-[#10b981]' : 'text-text-muted'}`}>
                                    {storeIvVelocity.state.includes('EXPANSION') || storeIvVelocity.state.includes('MOVE') ? '↑' : storeIvVelocity.state.includes('DROP') ? '↓' : '•'} {storeIvVelocity.state}
                                </span>
                            )}
                        </div>
                    </span>
                </div>
                <div className="w-[1px] h-[12px] bg-[#3f3f46]" />
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${connColor} shadow-[0_0_6px_currentcolor]`} />
                    <span className="text-[10px] font-bold text-[#71717a] tracking-widest">{connLabel}</span>
                </div>
            </div>

            <div className="flex items-center justify-end gap-2 px-3 border-l border-[#27272a] h-full">
                <div className="flex items-center gap-1.5 text-[#ef4444]">
                    <Zap size={10} className="fill-current shrink-0" />
                    <span className="text-[11px] font-black tracking-[0.2em] text-white/90 uppercase">TACTICAL OFFENSE</span>
                </div>
                <span className="text-[9px] font-bold tracking-widest text-[#71717a] ml-1">{rust.label}</span>
                <div className={`w-2 h-2 rounded-full ${rust.dotClass}`} />
            </div>
        </header>
    )
})

Header.displayName = 'Header'

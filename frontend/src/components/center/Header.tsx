import React from 'react'
import { fmtPrice } from '../../lib/utils'
import type { ConnectionStatus } from '../../types/dashboard'
import { Zap } from 'lucide-react'

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
            timeZone: 'America/New_York'
        })
        : '--:--:--'

    const connColor =
        status === 'connected' ? 'bg-[#10b981]' :
            status === 'connecting' ? 'bg-[#f59e0b]' :
                'bg-[#ef4444]'

    const ivRegimeColor =
        (ivRegime === 'HIGH' || ivRegime === 'EXTREME') ? 'text-[#ef4444]' :
            ivRegime === 'ELEVATED' ? 'text-[#f59e0b]' :
                'text-[#10b981]'

    const ivBadgeCls =
        (ivRegime === 'HIGH' || ivRegime === 'EXTREME')
            ? 'border-[#7f1d1d] text-[#ef4444] bg-[#450a0a]/50'
            : ivRegime === 'ELEVATED'
                ? 'border-[#92400e] text-[#f59e0b] bg-[#422006]/50'
                : 'border-[#065f46] text-[#10b981] bg-[#022c22]/50'

    return (
        /*
         * Grid 三列对齐三个面板宽度：
         *   左(280px)  =  ANALYSIS 面板
         *   中(1fr)    =  中央图表 + 遥测信息
         *   右(320px)  =  TACTICAL OFFENSE 面板
         */
        <header className="grid items-center h-[36px] border-b border-[#27272a] bg-[#060606] w-full font-sans selection:bg-transparent"
            style={{ gridTemplateColumns: '280px 1fr 320px' }}>

            {/* ── LEFT: ANALYSIS panel label ── */}
            <div className="flex items-center gap-2 px-3 border-r border-[#27272a] h-full">
                <span className="text-[11px] font-black tracking-[0.2em] text-white/90 uppercase">
                    ANALYSIS
                </span>
            </div>

            {/* ── CENTER: Telemetry bar ── */}
            <div className="flex items-center justify-center gap-5 h-full">

                {/* Brand */}
                <span className="font-black tracking-[0.15em] text-[#e4e4e7] text-[11px]">
                    SPX SENTINEL
                </span>

                <div className="w-[1px] h-[12px] bg-[#3f3f46]" />

                {/* Time */}
                <span className="font-mono text-[10px] text-[#71717a]">{timeStr} ET</span>

                <div className="w-[1px] h-[12px] bg-[#3f3f46]" />

                {/* Market open/close */}
                <span className={`text-[10px] font-black tracking-wider ${marketStatus === 'OPEN' ? 'text-[#10b981]' : 'text-[#52525b]'}`}>
                    {marketStatus}
                </span>

                <div className="w-[1px] h-[12px] bg-[#3f3f46]" />

                {/* SPY price */}
                <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-bold text-[#71717a]">SPY</span>
                    <span className="font-mono text-[12px] font-black text-[#e4e4e7]">{fmtPrice(spot)}</span>
                </div>

                <div className="w-[1px] h-[12px] bg-[#3f3f46]" />

                {/* IV */}
                <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-bold text-[#71717a]">IV</span>
                    <span className={`font-mono text-[12px] font-black ${ivRegimeColor}`}>
                        {ivPct != null ? `${ivPct.toFixed(2)}%` : '—'}
                    </span>
                    <span className={`text-[9px] font-black tracking-widest px-1.5 py-[1px] rounded-[2px] border ${ivBadgeCls}`}>
                        {ivRegime}
                    </span>
                </div>

                <div className="w-[1px] h-[12px] bg-[#3f3f46]" />

                {/* Connection */}
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${connColor} shadow-[0_0_6px_currentcolor]`} />
                    <span className="text-[10px] font-bold text-[#71717a] tracking-widest">RDS LIVE</span>
                </div>
            </div>

            {/* ── RIGHT: TACTICAL OFFENSE panel label ── */}
            <div className="flex items-center justify-end gap-2 px-3 border-l border-[#27272a] h-full">
                <div className="flex items-center gap-1.5 text-[#ef4444]">
                    <Zap size={10} className="fill-current shrink-0" />
                    <span className="text-[11px] font-black tracking-[0.2em] text-white/90 uppercase">
                        TACTICAL OFFENSE
                    </span>
                </div>
                <div className="w-2 h-2 rounded-full bg-[#10b981] shadow-[0_0_8px_rgba(16,185,129,0.6)] ml-1" />
            </div>

        </header>
    )
}
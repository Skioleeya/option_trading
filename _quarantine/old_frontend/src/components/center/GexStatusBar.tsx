import React from 'react'
import { fmtGex, fmtPrice } from '../../lib/utils'
import { Activity } from 'lucide-react'

/**
 * GexStatusBar — 最佳看盘比例版
 *
 * 公式基准（1536px 视口，中央面板 936px）:
 *   目标宽度  = 936 × φ⁻¹ ≈ 580px
 *   字号比例  = 标签 9px × φ ≈ 值 14px（黄金比例 φ = 1.618）
 *   高度      = 36px（与顶部 Header 等高，形成垂直呼应）
 */
interface Props {
    netGex: number | null
    callWall: number | null
    flipLevel: number | null
    putWall: number | null
}

export const GexStatusBar: React.FC<Props> = ({ netGex, callWall, flipLevel, putWall }) => {
    const isGexPos = netGex != null && netGex > 0
    const gexColor = netGex == null ? 'text-[#71717a]' : isGexPos ? 'text-[#10b981]' : 'text-[#ef4444]'

    return (
        /* 宽度锁定 580px，高度 36px，胶囊造型 */
        <div
            className="flex items-center bg-[#0d0d0f]/96 border border-[#3f3f46] rounded-full shadow-[0_0_24px_rgba(0,0,0,0.8)] font-sans overflow-hidden"
            style={{ width: '580px', height: '36px', padding: '0 16px' }}
        >
            {/* ── NET GEX ─────────────────────────────────── */}
            <div className="flex-1 flex items-center justify-center gap-2">
                <Activity size={14} className={gexColor} />
                <div className="flex flex-col leading-none">
                    <span className="text-[8px] font-bold tracking-[0.1em] text-[#52525b] uppercase">Net GEX</span>
                    <span className={`font-mono text-[13px] font-black tracking-tight ${gexColor}`}>
                        {fmtGex(netGex)}
                    </span>
                </div>
            </div>

            <div className="w-[1px] bg-[#3f3f46] h-4 shrink-0" />

            {/* ── CALL WALL ─────────────────────────────────── */}
            <div className="flex-1 flex items-center justify-center gap-2">
                <span className="text-[8px] font-bold tracking-[0.1em] text-[#71717a] uppercase whitespace-nowrap">Call Wall</span>
                <span className="px-1.5 py-[1px] rounded-[3px] bg-[#450a0a] border border-[#7f1d1d]/60 font-mono text-[12px] font-black text-[#ef4444]">
                    {fmtPrice(callWall)}
                </span>
            </div>

            <div className="w-[1px] bg-[#3f3f46] h-4 shrink-0" />

            {/* ── FLIP ─────────────────────────────────── */}
            <div className="flex-1 flex items-center justify-center gap-2">
                <span className="text-[8px] font-bold tracking-[0.1em] text-[#71717a] uppercase">Flip</span>
                <span className="px-1.5 py-[1px] rounded-[3px] bg-[#422006] border border-[#92400e]/60 font-mono text-[12px] font-black text-[#f59e0b]">
                    {fmtPrice(flipLevel)}
                </span>
            </div>

            <div className="w-[1px] bg-[#3f3f46] h-4 shrink-0" />

            {/* ── PUT WALL ─────────────────────────────────── */}
            <div className="flex-1 flex items-center justify-center gap-2">
                <span className="text-[8px] font-bold tracking-[0.1em] text-[#71717a] uppercase whitespace-nowrap">Put Wall</span>
                <span className="px-1.5 py-[1px] rounded-[3px] bg-[#022c22] border border-[#065f46]/60 font-mono text-[12px] font-black text-[#10b981]">
                    {fmtPrice(putWall)}
                </span>
            </div>
        </div>
    )
}
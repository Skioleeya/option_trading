import React from 'react'
import { fmtPrice } from '../../lib/utils'

interface PropTableRow {
    type_label: string
    type_bg: string
    type_text: string
    h1: number | null
    h2: number | null
    current: number | null
    dot_color: string
    current_border: string
    current_bg: string
    current_shadow: string
    current_text: string
    current_pulse: string
    wall_dyn_badge: string
    wall_dyn_color: string
    state: string
}

interface Props {
    rows: PropTableRow[]
}

export const WallMigration: React.FC<Props> = ({ rows }) => {
    return (
        <div className="p-2 pb-3 flex flex-col gap-1.5 font-sans bg-[#060606] selection:bg-transparent">
            {/* 1. S+ Terminal Header */}
            <div className="flex items-center mb-1 px-1">
                <div className="w-[2px] h-[10px] bg-[#d4d4d8] shadow-[0_0_4px_rgba(212,212,216,0.5)] mr-1.5"></div>
                <span className="text-[10px] font-black text-[#d4d4d8] tracking-widest leading-none">WALL MIGRATION</span>
            </div>

            {/* 2. Data Rows */}
            {rows.map((row, i) => {
                const isCall = row.type_label === 'C'

                // 1. 绝对身份隔离：即使后端传参，前端也必须锁死 C/P 徽章的基础色系
                const baseColor = isCall ? '#ef4444' : '#10b981'
                const baseBorder = isCall ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'
                const baseBg = isCall ? 'rgba(69,10,10,0.5)' : 'rgba(2,44,34,0.5)'

                // 2. 解析后端状态机
                const isBreached = row.state.includes('BREACHED')
                const isDecaying = row.state.includes('DECAYING')
                const isReinforced = row.state.includes('REINFORCED')
                const isRetreating = row.state.includes('RETREATING')

                // 3. 微章颜色直接信任后端的调色表
                const badgeColor = row.wall_dyn_color || '#a1a1aa'

                return (
                    <div key={i} className="flex items-center gap-1 px-1 relative">

                        {/* TYPE BADGE (C / P) - 永不褪色的身份锚点 */}
                        <div
                            className="w-6 h-[22px] flex items-center justify-center text-[10px] font-black flex-shrink-0 rounded-[2px]"
                            style={{
                                color: baseColor,
                                border: `1px solid ${baseBorder}`,
                                backgroundColor: baseBg,
                            }}
                        >
                            {row.type_label}
                        </div>

                        {/* T-2: Historical Ghost */}
                        <div className="flex-1 flex items-center justify-center h-[22px] bg-[#0a0a0a] border border-white/[0.03] rounded-[2px]">
                            <span className="font-mono text-[11px] font-medium text-[#3f3f46]">
                                {row.h1 != null ? fmtPrice(row.h1) : '—'}
                            </span>
                        </div>

                        {/* T-1: Historical Echo */}
                        <div className="flex-1 flex items-center justify-center h-[22px] bg-[#0a0a0a] border border-white/[0.06] rounded-[2px]">
                            <span className="font-mono text-[11px] font-medium text-[#71717a]">
                                {row.h2 != null ? fmtPrice(row.h2) : '—'}
                            </span>
                        </div>

                        {/* NOW: THE LIVE BATTLE LINE (融合后端意图与前端质感) */}
                        <div
                            className="flex-1 flex items-center justify-center h-[22px] relative overflow-hidden rounded-[2px] transition-colors duration-300"
                            style={{
                                // 边框直接采用后端传来的精细调色
                                border: `1px solid ${row.current_border || 'rgba(255,255,255,0.1)'}`,
                                // 背景底色控制：热寂态全黑，其他状态保留微弱质感
                                backgroundColor: isDecaying ? '#060606' : 'rgba(18,18,20,0.8)',
                            }}
                        >
                            {/* --- 光学渲染层 (Optical Rendering Layers) --- */}

                            {/* 1. BREACHED: 警报级白热内发光 */}
                            {isBreached && (
                                <div className="absolute inset-0 shadow-[inset_0_0_8px_rgba(255,255,255,0.3)] pointer-events-none"></div>
                            )}

                            {/* 2. REINFORCED: 日式终端内焰阴影 (压迫感) */}
                            {isReinforced && (
                                <div
                                    className="absolute inset-0 pointer-events-none"
                                    style={{
                                        boxShadow: `inset 0 0 10px ${isCall ? 'rgba(239,68,68,0.25)' : 'rgba(16,185,129,0.25)'}`
                                    }}
                                ></div>
                            )}

                            {/* 3. RETREATING: 琥珀色动态前导线 */}
                            {isRetreating && (
                                <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-[#eab308] shadow-[0_0_6px_rgba(234,179,8,0.8)] pointer-events-none"></div>
                            )}

                            {/* --- 数据层 --- */}
                            <span className={`font-mono text-[12px] relative z-10 ${isDecaying ? 'text-[#52525b] font-medium' :
                                isBreached ? 'text-white font-black drop-shadow-[0_0_4px_rgba(255,255,255,0.8)]' :
                                    'text-[#e4e4e7] font-bold'
                                }`}>
                                {row.current != null ? fmtPrice(row.current) : '—'}
                            </span>
                        </div>

                        {/* STATE BADGE - 右侧紧凑停靠 */}
                        <div className="w-[54px] flex items-center justify-end pl-1 flex-shrink-0">
                            <span
                                className={`text-[9px] font-mono font-bold tracking-wider truncate ${isBreached ? 'animate-pulse' : ''}`}
                                style={{
                                    color: badgeColor,
                                    // 仅为活跃状态添加自发光，热寂态 (DECAYING) 取消发光以彻底表现"死寂"
                                    textShadow: isDecaying ? 'none' : `0 0 6px ${badgeColor}60`
                                }}
                            >
                                {row.wall_dyn_badge}
                            </span>
                        </div>
                    </div>
                )
            })}
        </div>
    )
}

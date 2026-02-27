import React from 'react'
import { fmtVolume, fmtFlow } from '../../lib/utils'
import type { ActiveOption } from '../../types/dashboard'

interface Props {
    options: ActiveOption[]
}

export const ActiveOptions: React.FC<Props> = ({ options }) => {
    const sorted = [...options].sort((a, b) => b.volume - a.volume).slice(0, 5)

    return (
        <div className="p-2">
            <div className="flex items-center justify-between mb-1.5 px-0.5">
                <span className="text-[10px] font-bold tracking-wider text-text-primary">ACTIVE OPTIONS</span>
                <span className="text-[9px] font-medium text-text-muted">TOP BY VOLUME</span>
            </div>

            <table className="w-full text-2xs mono">
                <thead>
                    <tr className="text-text-muted border-b border-white/5 uppercase font-medium">
                        <th className="text-center py-1 w-6">#</th>
                        <th className="text-left py-1">SYM</th>
                        <th className="text-center py-1 w-4">T</th>
                        <th className="text-right py-1">STRIKE</th>
                        <th className="text-right py-1">IV</th>
                        <th className="text-right py-1">VOL</th>
                        <th className="text-right py-1 pr-1">FLOW</th>
                    </tr>
                </thead>
                <tbody>
                    {sorted.length === 0 && (
                        <tr>
                            <td colSpan={7} className="text-center py-2 text-text-secondary">—</td>
                        </tr>
                    )}
                    {sorted.map((opt, i) => {
                        const isCall = opt.option_type === 'CALL'
                        const flowNeg = opt.flow < 0
                        return (
                            <tr key={`${opt.symbol}-${opt.strike}-${opt.option_type}-${i}`}
                                className="border-b border-bg-border/50 hover:bg-bg-card transition-colors"
                            >
                                {/* Row marker + Rank */}
                                <td className="py-1 relative">
                                    <div className={`absolute left-0 top-[20%] bottom-[20%] w-[4px] rounded-r-sm ${isCall ? 'bg-accent-red' : 'bg-accent-green'}`} />
                                    <div className="text-center font-bold text-text-primary ml-1">{i + 1}</div>
                                </td>
                                <td className="py-0.5 pr-1 text-text-secondary">SPY</td>
                                <td className={`py-1 text-center font-bold ${isCall ? 'text-accent-red' : 'text-accent-green'}`}>
                                    {isCall ? 'C' : 'P'}
                                </td>
                                <td className="py-1 text-right text-text-primary font-bold">
                                    {opt.strike.toFixed(2)}
                                </td>
                                <td className="py-1 text-right text-[#40c4ff]">
                                    {opt.implied_volatility ? `${(opt.implied_volatility * 100).toFixed(1)}%` : '—'}
                                </td>
                                <td className="py-1 text-right">
                                    <span className="px-1.5 py-0.5 rounded-[4px] text-[10px] font-bold bg-white/5 border border-white/10">
                                        {(opt as any).flow_volume_label || fmtVolume(opt.volume)}
                                    </span>
                                </td>
                                <td className={`py-1 text-right font-bold transition-all duration-500 pr-1 ${(opt as any).flow_color || (flowNeg ? 'text-accent-green' : 'text-accent-red')} ${(opt as any).flow_glow || ''}`}>
                                    {(opt as any).flow_deg_formatted || fmtFlow(opt.flow)}
                                </td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}

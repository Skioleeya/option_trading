import React from 'react'
import { fmtPrice, fmtVolume, fmtFlow } from '../../lib/utils'
import type { ActiveOption } from '../../types/dashboard'

interface Props {
    options: ActiveOption[]
}

export const ActiveOptions: React.FC<Props> = ({ options }) => {
    const sorted = [...options].sort((a, b) => b.volume - a.volume).slice(0, 5)

    return (
        <div className="p-2">
            <div className="flex items-center justify-between mb-2">
                <span className="section-header">ACTIVE OPTIONS</span>
                <span className="section-header text-text-muted">TOP BY VOLUME</span>
            </div>

            <table className="w-full text-2xs mono">
                <thead>
                    <tr className="text-text-secondary border-b border-bg-border">
                        <th className="text-left py-0.5 pr-1 w-4">#</th>
                        <th className="text-left py-0.5 pr-1">SYM</th>
                        <th className="text-left py-0.5 pr-1 w-4">T</th>
                        <th className="text-right py-0.5 pr-1">STRIKE</th>
                        <th className="text-right py-0.5 pr-1">IV</th>
                        <th className="text-right py-0.5 pr-1">VOL</th>
                        <th className="text-right py-0.5">FLOW</th>
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
                                {/* # with color bar */}
                                <td className="py-0.5 pr-1">
                                    <div className="flex items-center gap-0.5">
                                        <div className={`w-0.5 h-3 rounded-full ${isCall ? 'bg-accent-red' : 'bg-accent-green'}`} />
                                        <span className="text-text-secondary">{i + 1}</span>
                                    </div>
                                </td>
                                <td className="py-0.5 pr-1 text-text-secondary">SPY</td>
                                <td className={`py-0.5 pr-1 font-bold ${isCall ? 'text-accent-red' : 'text-accent-green'}`}>
                                    {isCall ? 'C' : 'P'}
                                </td>
                                <td className="py-0.5 pr-1 text-right text-text-primary">
                                    {fmtPrice(opt.strike)}
                                </td>
                                <td className="py-0.5 pr-1 text-right text-text-secondary">
                                    {opt.implied_volatility ? `${(opt.implied_volatility * 100).toFixed(1)}%` : '—'}
                                </td>
                                <td className="py-0.5 pr-1 text-right">
                                    <span className={`px-1 rounded text-2xs font-bold ${isCall ? 'bg-accent-red/20 text-accent-red' : 'bg-accent-green/20 text-accent-green'}`}>
                                        {fmtVolume(opt.volume)}
                                    </span>
                                </td>
                                <td className={`py-0.5 text-right font-bold ${flowNeg ? 'text-accent-red' : 'text-accent-green'}`}>
                                    {fmtFlow(opt.flow)}
                                </td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}

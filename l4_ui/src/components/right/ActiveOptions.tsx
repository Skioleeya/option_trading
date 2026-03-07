/**
 * ActiveOptions — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { fmtVolume, fmtFlow } from '../../lib/utils'
import type { ActiveOption } from '../../types/dashboard'
import { useDashboardStore } from '../../store/dashboardStore'
import { normalizeActiveOptions } from './activeOptionsModel'

const selectActiveOptions = (s: ReturnType<typeof useDashboardStore.getState>) =>
    (s.payload?.agent_g?.data?.ui_state?.active_options ?? null) as ActiveOption[] | null

interface Props { options?: ActiveOption[] }

export const ActiveOptions: React.FC<Props> = memo(({ options: propOptions }) => {
    const storeOptions = useDashboardStore(selectActiveOptions)
    const options: ActiveOption[] = normalizeActiveOptions(storeOptions ?? propOptions ?? [], 5)

    // THE BACKEND ALREADY SORTS BY IMPACT_INDEX. 
    // We preserve the order provided by the L3 Presenter.
    const sorted = options

    return (
        <div className="p-2">
            <div className="flex items-center justify-between mb-1.5 px-0.5">
                <span className="text-[10px] font-bold tracking-wider text-text-primary uppercase">Active Options</span>
                <span className="text-[9px] font-medium text-[#ff9800]">TOP BY IMPACT (OFII)</span>
            </div>

            <table className="w-full text-2xs mono">
                <thead>
                    <tr className="text-white border-b border-white/5 uppercase font-medium">
                        <th className="text-center py-1 w-6">#</th>
                        <th className="text-left py-1">SYM</th>
                        <th className="text-center py-1 w-4">T</th>
                        <th className="text-right py-1">STRIKE</th>
                        <th className="text-right py-1">IMP</th>
                        <th className="text-right py-1">VOL</th>
                        <th className="text-right py-1 pr-1">FLOW</th>
                    </tr>
                </thead>
                <tbody>
                    {sorted.length === 0 && (
                        <tr><td colSpan={7} className="text-center py-2 text-text-secondary">—</td></tr>
                    )}
                    {sorted.map((opt, i) => {
                        const isCall = opt.option_type === 'CALL'
                        const flowNeg = opt.flow < 0
                        const impactValue = typeof opt.impact_index === 'number' ? opt.impact_index : 0
                        // Use the sweep glow if provided by backend
                        const rowGlow = opt.flow_glow || ''

                        return (
                            <tr key={`${opt.symbol}-${opt.strike}-${opt.option_type}-${i}`}
                                className={`border-b border-bg-border/50 hover:bg-bg-card transition-colors ${rowGlow}`}>
                                <td className="py-1 relative">
                                    <div className={`absolute left-0 top-[20%] bottom-[20%] w-[4px] rounded-r-sm ${isCall ? 'bg-accent-red' : 'bg-accent-green'}`} />
                                    <div className="text-center font-bold text-text-primary ml-1">{i + 1}</div>
                                </td>
                                <td className="py-0.5 pr-1 text-text-secondary">SPY</td>
                                <td className={`py-1 text-center font-bold ${isCall ? 'text-accent-red' : 'text-accent-green'}`}>
                                    {isCall ? 'C' : 'P'}
                                </td>
                                <td className="py-1 text-right text-text-primary font-bold">{opt.strike.toFixed(2)}</td>
                                <td className="py-1 text-right font-bold text-white/90">
                                    {impactValue.toFixed(2)}
                                </td>
                                <td className="py-1 text-right">
                                    <span className="px-1.5 py-0.5 rounded-[4px] text-[10px] font-bold bg-white/5 border border-white/10">
                                        {(opt as any).flow_volume_label || fmtVolume(opt.volume)}
                                    </span>
                                </td>
                                <td className={`py-1 text-right font-bold transition-all duration-500 pr-1 ${(opt as any).flow_color || (flowNeg ? 'text-accent-green' : 'text-accent-red')}`}>
                                    {(opt as any).flow_deg_formatted || fmtFlow(opt.flow)}
                                </td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
})

ActiveOptions.displayName = 'ActiveOptions'

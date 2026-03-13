/**
 * ActiveOptions — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { fmtVolume, fmtFlow } from '../../lib/utils'
import type { ActiveOption } from '../../types/dashboard'
import { useDashboardStore, selectUiStateActiveOptions } from '../../store/dashboardStore'
import { normalizeActiveOptions } from './activeOptionsModel'
import { ACTIVE_OPTIONS_FIXED_ROWS } from './activeOptionsTheme'

interface Props {
    options?: ActiveOption[]
    preferProp?: boolean
}

export const ActiveOptions: React.FC<Props> = memo(({ options: propOptions, preferProp = false }) => {
    const storeOptions = useDashboardStore(selectUiStateActiveOptions)
    const source = preferProp
        ? (propOptions ?? storeOptions ?? [])
        : (storeOptions ?? propOptions ?? [])
    const options: ActiveOption[] = normalizeActiveOptions(source, ACTIVE_OPTIONS_FIXED_ROWS)
    const isDegraded = options.length > 0 && options.every((opt) => Boolean(opt.is_placeholder))

    return (
        <div className="p-2">
            <div className="flex items-center justify-between mb-1.5 px-0.5">
                <span className="text-[10px] font-bold tracking-wider text-text-primary uppercase">Active Options</span>
                <span className={`text-[9px] font-medium ${isDegraded ? 'text-text-secondary' : 'text-accent-amber'}`}>{isDegraded ? 'DEGRADED' : 'TOP BY VOL'}</span>
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
                    {options.map((opt, i) => {
                        const isPlaceholder = Boolean(opt.is_placeholder)
                        const isCall = !isPlaceholder && opt.option_type === 'CALL'
                        const flowNeg = opt.flow < 0
                        const impactValue = typeof opt.impact_index === 'number' ? opt.impact_index : 0
                        const rowGlow = isPlaceholder ? '' : (opt.flow_glow || '')
                        const slot = opt.slot_index && opt.slot_index > 0 ? opt.slot_index : (i + 1)

                        return (
                            <tr key={`slot-${slot}`}
                                data-slot={slot}
                                data-placeholder={isPlaceholder ? 'true' : 'false'}
                                className={`border-b border-bg-border/50 hover:bg-bg-card transition-colors ${rowGlow}`}>
                                <td className="py-1 relative">
                                    {!isPlaceholder && (
                                        <div className={`absolute left-0 top-[20%] bottom-[20%] w-[4px] rounded-r-sm ${isCall ? 'bg-accent-red' : 'bg-accent-green'}`} />
                                    )}
                                    <div className="text-center font-bold text-text-primary ml-1">{slot}</div>
                                </td>
                                <td className="py-0.5 pr-1 text-text-secondary">{isPlaceholder ? '—' : (opt.symbol || 'SPY')}</td>
                                <td className={`py-1 text-center font-bold ${isPlaceholder ? 'text-text-secondary' : (isCall ? 'text-accent-red' : 'text-accent-green')}`}>
                                    {isPlaceholder ? '—' : (isCall ? 'C' : 'P')}
                                </td>
                                <td className="py-1 text-right text-text-primary font-bold">{isPlaceholder ? '—' : opt.strike.toFixed(2)}</td>
                                <td className="py-1 text-right font-bold text-white/90">
                                    {isPlaceholder ? '—' : impactValue.toFixed(2)}
                                </td>
                                <td className="py-1 text-right">
                                    <span className="px-1.5 py-0.5 rounded-[4px] text-[10px] font-bold bg-white/5 border border-white/10">
                                        {isPlaceholder ? '—' : (opt.flow_volume_label || fmtVolume(opt.volume))}
                                    </span>
                                </td>
                                <td className={`py-1 text-right font-bold transition-all duration-500 pr-1 ${isPlaceholder ? 'text-text-secondary' : (opt.flow_color || (flowNeg ? 'text-accent-green' : 'text-accent-red'))}`}>
                                    {isPlaceholder ? '—' : (opt.flow_deg_formatted || fmtFlow(opt.flow))}
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


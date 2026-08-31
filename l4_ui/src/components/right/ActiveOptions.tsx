/**
 * ActiveOptions — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { fmtVolume, fmtFlow, fmtImpact } from '../../lib/utils'
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
    const allPlaceholder = options.length > 0 && options.every((opt) => Boolean(opt.is_placeholder))
    const hasDegradedSignal = options.some((opt) => {
        if (opt.is_placeholder) return false
        return String(opt.flow_signal_state ?? '').toUpperCase() === 'DEGRADED'
    })
    const isDegraded = allPlaceholder || hasDegradedSignal

    return (
        <div style={{ padding: 'var(--l4-panel-pad)' }}>
            <div className="flex items-center justify-between mb-1.5 px-0.5">
                <span className="font-bold tracking-wider text-text-primary uppercase" style={{ fontSize: 'var(--l4-font-10)' }}>Active Options</span>
                <span className={`font-medium ${isDegraded ? 'text-text-secondary' : 'text-accent-amber'}`} style={{ fontSize: 'var(--l4-font-9)' }}>{isDegraded ? 'DEGRADED' : 'TOP BY VOL'}</span>
            </div>

            <table className="w-full mono table-auto l4-active-options__table" style={{ fontSize: 'var(--l4-font-10)' }}>
                <thead>
                    <tr className="text-white border-b border-white/5 uppercase font-medium">
                        <th className="text-center py-1 w-6 whitespace-nowrap">#</th>
                        <th className="text-left py-1 whitespace-nowrap">SYM</th>
                        <th className="text-center py-1 w-4 whitespace-nowrap">T</th>
                        <th className="text-right py-1 whitespace-nowrap">STRIKE</th>
                        <th className="text-right py-1 whitespace-nowrap">IMP</th>
                        <th className="text-right py-1 whitespace-nowrap">VOL</th>
                        <th className="text-right py-1 pr-1 whitespace-nowrap">FLOW</th>
                    </tr>
                </thead>
                <tbody>
                    {options.map((opt, i) => {
                        const isPlaceholder = Boolean(opt.is_placeholder)
                        const isCall = !isPlaceholder && opt.option_type === 'CALL'
                        const impactValue = typeof opt.impact_index === 'number' ? opt.impact_index : 0
                        const slot = opt.slot_index && opt.slot_index > 0 ? opt.slot_index : (i + 1)

                        return (
                            <tr key={`slot-${slot}`}
                                data-slot={slot}
                                data-placeholder={isPlaceholder ? 'true' : 'false'}
                                className="border-b border-bg-border/50 hover:bg-bg-card">
                                <td className="py-0.5 relative whitespace-nowrap">
                                    {!isPlaceholder && (
                                        <div className={`absolute left-0 top-[20%] bottom-[20%] rounded-r-sm ${isCall ? 'bg-accent-red' : 'bg-accent-green'}`} style={{ width: 'var(--l4-row-accent-w)' }} />
                                    )}
                                    <div className="text-center font-bold text-text-primary ml-1">{slot}</div>
                                </td>
                                <td className="py-0.5 pr-0.5 text-text-secondary whitespace-nowrap">{isPlaceholder ? '—' : (opt.symbol || 'SPY')}</td>
                                <td className={`py-0.5 text-center font-bold whitespace-nowrap ${isPlaceholder ? 'text-text-secondary' : (isCall ? 'text-accent-red' : 'text-accent-green')}`}>
                                    {isPlaceholder ? '—' : (isCall ? 'C' : 'P')}
                                </td>
                                <td className="py-0.5 text-right text-text-primary font-bold whitespace-nowrap">{isPlaceholder ? '—' : opt.strike.toFixed(2)}</td>
                                <td className="py-0.5 text-right font-bold text-white/90 whitespace-nowrap">
                                    {isPlaceholder ? '—' : fmtImpact(impactValue)}
                                </td>
                                <td className="py-0.5 text-right whitespace-nowrap">
                                    <span className="px-1 py-0.5 rounded-[4px] font-bold bg-white/5 border border-white/10" style={{ fontSize: 'var(--l4-font-9)' }}>
                                        {isPlaceholder ? '—' : (opt.flow_volume_label || fmtVolume(opt.volume))}
                                    </span>
                                </td>
                                <td className={`py-0.5 text-right font-bold pr-1 whitespace-nowrap ${isPlaceholder ? 'text-text-secondary' : opt.flow_color}`}>
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

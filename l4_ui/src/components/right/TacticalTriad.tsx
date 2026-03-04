/**
 * TacticalTriad — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { Activity, Clock, Triangle, Activity as Pulse } from 'lucide-react'
import { useDashboardStore } from '../../store/dashboardStore'

const selectTacticalTriad = (s: ReturnType<typeof useDashboardStore.getState>) =>
    s.payload?.agent_g?.data?.ui_state?.tactical_triad ?? null

interface Props { uiState?: any }

const ZERO = {
    vrp: { value: '—', state_label: 'VRP', color_class: 'text-text-secondary', border_class: 'border-bg-border', bg_class: 'bg-[#1e1e1e]', shadow_class: 'shadow-none', animation: '', sub_intensity: 'LOW', sub_label: 'NEUTRAL' },
    charm: { value: '—', state_label: 'STABLE', color_class: 'text-text-secondary', border_class: 'border-bg-border', bg_class: 'bg-[#1e1e1e]', shadow_class: 'shadow-none', multiplier: null, sub_intensity: 'LOW', sub_label: 'STABLE' },
    svol: { value: '—', state_label: 'S-VOL', color_class: 'text-text-secondary', border_class: 'border-bg-border', bg_class: 'bg-[#1e1e1e]', shadow_class: 'shadow-none', animation: '', sub_intensity: 'LOW', sub_label: 'NEUTRAL' },
}

export const TacticalTriad: React.FC<Props> = memo(({ uiState: propState }) => {
    const storeState = useDashboardStore(selectTacticalTriad)
    const state = storeState ?? propState ?? ZERO
    const { vrp, charm, svol } = state

    return (
        <div className="border-t border-bg-border p-2">
            <div className="flex items-center justify-between mb-2">
                <span className="section-header">TACTICAL TRIAD</span>
                <span className="section-header text-text-muted">S-VOL / CHARM / VRP</span>
            </div>

            <div className="grid grid-cols-3 gap-1.5">
                {/* VRP */}
                <div className="flex flex-col items-center">
                    <div className={`w-full border ${vrp.border_class} ${vrp.bg_class} rounded flex flex-col items-center justify-center py-1.5 ${vrp.shadow_class} mb-1.5`}>
                        <span className={`${vrp.color_class} ${vrp.animation} font-bold text-xs leading-none mb-0.5`}>$</span>
                        <span className={`${vrp.color_class} ${vrp.animation} text-lg font-bold leading-tight`}>{vrp.value}</span>
                        <span className={`${vrp.color_class} ${vrp.animation} font-bold text-[9px] leading-tight`}>{vrp.state_label}</span>
                        <span className={`${vrp.color_class} ${vrp.animation} font-bold text-[9px] leading-tight mt-[1px]`}>VRP</span>
                    </div>
                    <div className="flex items-center gap-1 text-text-muted mb-0.5"><Activity size={10} /><span className="text-[10px] font-bold tracking-wider">{vrp.sub_intensity}</span></div>
                    <span className="text-[10px] font-bold tracking-wider text-text-primary">{vrp.sub_label}</span>
                </div>

                {/* CHARM */}
                <div className="flex flex-col items-center">
                    <div className={`w-full border ${charm.border_class} ${charm.bg_class} rounded flex flex-col items-center justify-center py-1.5 ${charm.shadow_class} mb-1.5`}>
                        <div className={`flex items-center ${charm.color_class} mb-0.5 gap-0.5`}>
                            <Pulse size={10} />
                            {charm.multiplier && <span className="font-bold text-[9px] leading-none">{charm.multiplier}</span>}
                        </div>
                        <span className={`${charm.color_class} text-lg font-bold leading-tight`}>{charm.value}</span>
                        <span className={`${charm.color_class} font-bold text-[9px] leading-tight`}>{charm.state_label}</span>
                        <span className={`${charm.color_class} font-bold text-[9px] leading-tight mt-[1px]`}>CHARM</span>
                    </div>
                    <div className="flex items-center gap-1 text-text-muted mb-0.5"><Clock size={10} /><span className="text-[10px] font-bold tracking-wider">{charm.sub_intensity}</span></div>
                    <span className="text-[10px] font-bold tracking-wider text-text-primary">{charm.sub_label}</span>
                </div>

                {/* S-VOL */}
                <div className="flex flex-col items-center">
                    <div className={`w-full border ${svol.border_class} ${svol.bg_class} rounded flex flex-col items-center justify-center py-1.5 ${svol.shadow_class} mb-1.5`}>
                        <Pulse size={10} className={`${svol.color_class} ${svol.animation} mb-0.5`} />
                        <span className={`${svol.color_class} ${svol.animation} text-lg font-bold leading-tight`}>{svol.value}</span>
                        <span className={`${svol.color_class} ${svol.animation} font-bold text-[9px] leading-tight`}>{svol.state_label}</span>
                        <span className={`${svol.color_class} ${svol.animation} font-bold text-[9px] leading-tight mt-[1px]`}>S-VOL</span>
                    </div>
                    <div className="flex items-center gap-1 text-text-muted mb-0.5"><Triangle size={10} /><span className="text-[10px] font-bold tracking-wider">{svol.sub_intensity}</span></div>
                    <span className="text-[10px] font-bold tracking-wider text-text-primary">{svol.sub_label}</span>
                </div>
            </div>
        </div>
    )
})

TacticalTriad.displayName = 'TacticalTriad'

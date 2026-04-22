/**
 * TacticalTriad — Phase 3: Zustand field-level selector
 * DOM/CSS/Layout: UNCHANGED
 */
import React, { memo } from 'react'
import { Activity, Clock, Triangle, Activity as Pulse } from 'lucide-react'
import { useDashboardStore, selectUiStateTacticalTriad } from '../../store/dashboardStore'
import type { TacticalTriadState } from '../../types/dashboard'
import { normalizeTacticalTriadState } from './tacticalTriadModel'

interface Props {
    uiState?: TacticalTriadState | null
    preferProp?: boolean
}

export const TacticalTriad: React.FC<Props> = memo(({ uiState: propState, preferProp = false }) => {
    const storeState = useDashboardStore(selectUiStateTacticalTriad)
    const state = normalizeTacticalTriadState(preferProp ? (propState ?? storeState) : (storeState ?? propState))
    const { vrp, charm, svol } = state

    return (
        <div className="border-t border-bg-border" style={{ padding: 'var(--l4-panel-pad)' }}>
            <div className="flex items-center justify-between mb-2">
                <span className="section-header">TACTICAL TRIAD</span>
                <span className="section-header text-text-muted">MICRO DYNAMICS</span>
            </div>

            <div className="grid grid-cols-3" style={{ gap: 'var(--l4-panel-gap)' }}>
                {/* VRP */}
                <div className="flex flex-col items-center">
                    <div className={`w-full border ${vrp.border_class} ${vrp.bg_class} rounded flex flex-col items-center justify-center ${vrp.shadow_class} mb-1.5`} style={{ paddingBlock: 'var(--l4-card-pad)' }}>
                        <span className={`${vrp.color_class} font-bold leading-none mb-0.5`} style={{ fontSize: 'var(--l4-font-12)' }}>$</span>
                        <span className={`${vrp.color_class} font-bold leading-tight`} style={{ fontSize: 'var(--l4-triad-value-font)' }}>{vrp.value}</span>
                        <span className={`${vrp.color_class} font-bold leading-tight`} style={{ fontSize: 'var(--l4-font-9)' }}>{vrp.state_label}</span>
                        <span className={`${vrp.color_class} font-bold leading-tight mt-[1px]`} style={{ fontSize: 'var(--l4-font-9)' }}>VRP</span>
                    </div>
                    <div className="flex items-center gap-1 text-text-muted mb-0.5"><Activity size={10} /><span className="font-bold tracking-wider" style={{ fontSize: 'var(--l4-font-10)' }}>{vrp.sub_intensity}</span></div>
                    <span className="font-bold tracking-wider text-text-primary" style={{ fontSize: 'var(--l4-font-10)' }}>{vrp.sub_label}</span>
                </div>

                {/* CHARM */}
                <div className="flex flex-col items-center">
                    <div className={`w-full border ${charm.border_class} ${charm.bg_class} rounded flex flex-col items-center justify-center ${charm.shadow_class} mb-1.5`} style={{ paddingBlock: 'var(--l4-card-pad)' }}>
                        <div className={`flex items-center ${charm.color_class} mb-0.5 gap-0.5`}>
                            <Pulse size={10} />
                            {charm.multiplier && <span className="font-bold leading-none" style={{ fontSize: 'var(--l4-font-9)' }}>{charm.multiplier}</span>}
                        </div>
                        <span className={`${charm.color_class} font-bold leading-tight`} style={{ fontSize: 'var(--l4-triad-value-font)' }}>{charm.value}</span>
                        <span className={`${charm.color_class} font-bold leading-tight`} style={{ fontSize: 'var(--l4-font-9)' }}>{charm.state_label}</span>
                        <span className={`${charm.color_class} font-bold leading-tight mt-[1px]`} style={{ fontSize: 'var(--l4-font-9)' }}>CHARM</span>
                    </div>
                    <div className="flex items-center gap-1 text-text-muted mb-0.5"><Clock size={10} /><span className="font-bold tracking-wider" style={{ fontSize: 'var(--l4-font-10)' }}>{charm.sub_intensity}</span></div>
                    <span className="font-bold tracking-wider text-text-primary" style={{ fontSize: 'var(--l4-font-10)' }}>{charm.sub_label}</span>
                </div>

                {/* S-VOL */}
                <div className="flex flex-col items-center">
                    <div className={`w-full border ${svol.border_class} ${svol.bg_class} rounded flex flex-col items-center justify-center ${svol.shadow_class} mb-1.5`} style={{ paddingBlock: 'var(--l4-card-pad)' }}>
                        <Pulse size={10} className={`${svol.color_class} mb-0.5`} />
                        <span className={`${svol.color_class} font-bold leading-tight`} style={{ fontSize: 'var(--l4-triad-value-font)' }}>{svol.value}</span>
                        <span className={`${svol.color_class} font-bold leading-tight`} style={{ fontSize: 'var(--l4-font-9)' }}>{svol.state_label}</span>
                        <span className={`${svol.color_class} font-bold leading-tight mt-[1px]`} style={{ fontSize: 'var(--l4-font-9)' }}>S-VOL</span>
                    </div>
                    <div className="flex items-center gap-1 text-text-muted mb-0.5"><Triangle size={10} /><span className="font-bold tracking-wider" style={{ fontSize: 'var(--l4-font-10)' }}>{svol.sub_intensity}</span></div>
                    <span className="font-bold tracking-wider text-text-primary" style={{ fontSize: 'var(--l4-font-10)' }}>{svol.sub_label}</span>
                </div>
            </div>
        </div>
    )
})

TacticalTriad.displayName = 'TacticalTriad'

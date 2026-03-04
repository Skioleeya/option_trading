import React from 'react'
import { AlertCircle } from 'lucide-react'

interface Props {
    uiState: any
}

export const SkewDynamics: React.FC<Props> = ({ uiState }) => {
    // If no backend state is loaded yet, fall back to safe defaults
    const state = uiState ?? {
        value: "—",
        state_label: "NEUTRAL",
        color_class: "text-text-secondary",
        border_class: "border-bg-border",
        bg_class: "bg-[#1e1e1e]",
        shadow_class: "shadow-none",
        badge: "badge-neutral"
    }

    return (
        <div className="border-t border-bg-border p-2">
            <div className="flex items-center justify-between mb-1">
                <span className="section-header">SKEW DYNAMICS</span>
                <span className="section-header text-text-muted">IV SKEW ANALYSIS</span>
            </div>
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                    <div className="w-5 h-5 rounded flex items-center justify-center bg-[#1e1e1e] border border-bg-border">
                        <AlertCircle size={10} className="text-text-secondary" />
                    </div>
                    <div>
                        <div className="section-header">IV SKEW</div>
                        <div className={`badge ${state.badge} text-[9px] px-1 py-0! tracking-wider bg-[#1e1e1e]`}>
                            {state.state_label}
                        </div>
                    </div>
                </div>
                <span className={`mono text-xl font-bold ${state.color_class}`}>{state.value}</span>
            </div>
        </div>
    )
}

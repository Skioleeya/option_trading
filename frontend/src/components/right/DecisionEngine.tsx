import React from 'react'
import { Anchor, Activity, BarChart2 } from 'lucide-react'
import type { FusedSignal } from '../../types/dashboard'

interface Props {
    fused: FusedSignal | null
}

export const DecisionEngine: React.FC<Props> = ({ fused }) => {
    const weights = fused?.weights ?? { iv: 0, wall: 0, vanna: 0, mtf: 0 }
    const components = fused?.components ?? {}

    const quadrants = [
        {
            key: 'iv',
            label: 'IV VEL',
            icon: <Zap />,
            pct: Math.round((weights.iv ?? 0) * 100),
            conf: Math.round((components.iv?.confidence ?? 0) * 100),
        },
        {
            key: 'wall',
            label: 'WALL DYN',
            icon: <Anchor />,
            pct: Math.round((weights.wall ?? 0) * 100),
            conf: Math.round((components.wall?.confidence ?? 0) * 100),
        },
        {
            key: 'vanna',
            label: 'VANNA',
            icon: <Activity />,
            pct: Math.round((weights.vanna ?? 0) * 100),
            conf: Math.round((components.vanna?.confidence ?? 0) * 100),
        },
        {
            key: 'mtf',
            label: 'MTF',
            icon: <BarChart2 />,
            pct: Math.round((weights.mtf ?? 0) * 100),
            conf: Math.round((components.mtf?.confidence ?? 0) * 100),
        },
    ]

    return (
        <div className="p-2 space-y-2">
            <div className="flex items-center justify-between mb-1">
                <span className="section-header">DECISION ENGINE</span>
                <span className="section-header text-text-muted">FUSION SIGNAL</span>
            </div>

            <div className="grid grid-cols-2 gap-1.5">
                {quadrants.map((q) => (
                    <div key={q.key} className="bg-bg-card rounded p-1.5 border border-bg-border">
                        <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-1 section-header">
                                {React.cloneElement(q.icon as React.ReactElement, { size: 9, className: 'text-text-secondary' })}
                                {q.label}
                            </div>
                            <span className="mono text-sm font-bold text-text-primary">{q.pct}%</span>
                        </div>
                        {/* Progress bar (weight) */}
                        <div className="progress-track">
                            <div
                                className="progress-fill bg-accent-amber"
                                style={{ width: `${q.pct}%` }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

// Lucide Zap inline since we need dynamic icon refs
const Zap = () => (
    <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
)

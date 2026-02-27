import React from 'react'
import { Anchor, Activity, Minus, Zap } from 'lucide-react'

interface Props {
    uiState: {
        net_gex: { label: string; badge: string }
        wall_dyn: { label: string; badge: string }
        vanna: { label: string; badge: string }
        momentum: { label: string; badge: string }
    }
    sideState: string
}

// Stat card with title, icon, badge, and optional value
const StatCard: React.FC<{
    title: string
    icon?: React.ReactNode
    badge?: React.ReactNode
    value?: string
}> = ({ title, icon, badge, value }) => (
    <div className="rounded p-1.5 space-y-1.5"
        style={{ border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.02)' }}>
        <div className="flex items-center gap-1">
            <span className="section-header">{title}</span>
            {icon && <span className="text-text-secondary">{icon}</span>}
        </div>
        <div className="flex items-center gap-1.5">
            {badge}
            {value && <span className="mono text-xs font-bold text-text-primary">{value}</span>}
        </div>
    </div>
)

export const MicroStats: React.FC<Props> = ({
    uiState,
    sideState,
}) => {
    return (
        <div className="p-2 space-y-2">
            {/* Section title */}
            <div className="section-header tracking-widest">MICRO STATS</div>

            {/* 2×2 grid */}
            <div className="grid grid-cols-2 gap-1.5">

                {/* NET GEX */}
                <StatCard
                    title="NET GEX"
                    icon={<Activity size={9} className="text-[#a855f7]" />}
                    badge={
                        <span className={`badge ${uiState.net_gex.badge}`}>
                            {uiState.net_gex.label}
                        </span>
                    }
                />

                {/* WALL DYN */}
                <StatCard
                    title="WALL DYN"
                    icon={<Anchor size={9} className="text-accent-amber" />}
                    badge={
                        <span className={`badge ${uiState.wall_dyn.badge}`}>
                            {uiState.wall_dyn.label}
                        </span>
                    }
                />

                {/* MOMENTUM */}
                <StatCard
                    title="MOMENTUM"
                    badge={
                        <Minus size={14} className="text-text-secondary" />
                    }
                    value={uiState.momentum.label !== '—' ? uiState.momentum.label : undefined}
                />

                {/* VANNA */}
                <StatCard
                    title="VANNA"
                    icon={<Zap size={9} className="text-accent-cyan" />}
                    badge={
                        <span className={`badge ${uiState.vanna.badge}`}>
                            {uiState.vanna.label}
                        </span>
                    }
                />
            </div>

            {/* SIDE — separate row below */}
            <div className="rounded p-1.5"
                style={{ border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.02)' }}>
                <div className="section-header mb-1">SIDE</div>
                {sideState ? (
                    <span className="badge badge-purple">{sideState}</span>
                ) : null}
            </div>
        </div>
    )
}

import React from 'react'
import { Anchor, Activity, Minus, Zap } from 'lucide-react'

interface Props {
    uiState: {
        net_gex: { label: string; badge: string }
        wall_dyn: { label: string; badge: string }
        vanna: { label: string; badge: string }
        momentum: { label: string; badge: string }
    }
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
        <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
                <span className="section-header text-white/90">{title}</span>
                {icon && <span className="opacity-100 drop-shadow-md">{icon}</span>}
            </div>
            {value && <span className="mono text-xs font-bold text-text-primary">{value}</span>}
        </div>
        <div className="flex items-center">
            {badge}
            {value && <span className="mono text-xs font-bold text-text-primary">{value}</span>}
        </div>
    </div>
)

export const MicroStats: React.FC<Props> = ({
    uiState,
}) => {
    return (
        <div className="p-1 pb-4 space-y-1.5 bg-[#0a0c10]">
            {/* Section title */}
            <div className="flex items-center gap-2 px-1">
                <div className="w-1.5 h-1.5 rounded-sm bg-white/80" />
                <span className="section-header text-white/90 tracking-widest">MICRO STATS</span>
            </div>

            {/* 2×2 grid */}
            <div className="grid grid-cols-2 gap-1 px-1">

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
                    icon={<Minus size={14} className="text-white/60" />}
                    badge={
                        <span className={`badge ${uiState.momentum.badge}`}>
                            {uiState.momentum.label}
                        </span>
                    }
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
        </div>
    )
}

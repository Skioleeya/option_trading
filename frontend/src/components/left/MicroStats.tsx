import React from 'react'
import { Anchor, Zap, Minus } from 'lucide-react'
import { fmtGex, gexRegimeBadge, gexRegimeLabel } from '../../lib/utils'
import type { GexRegime } from '../../types/dashboard'

interface Props {
    netGex: number | null
    gexRegime: GexRegime
    wallDynState: string
    momentumState: string
    vannaState: string
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
    netGex,
    gexRegime,
    wallDynState,
    momentumState,
    vannaState,
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
                    icon={<Zap size={9} className="text-accent-red" />}
                    badge={
                        <span className={`badge ${gexRegimeBadge(gexRegime)}`}>
                            {gexRegimeLabel(gexRegime)}
                        </span>
                    }
                    value={netGex != null ? fmtGex(netGex) : undefined}
                />

                {/* WALL DYN */}
                <StatCard
                    title="WALL DYN"
                    icon={<Anchor size={9} className="text-accent-amber" />}
                    badge={
                        <span className={`badge ${wallDynBadge(wallDynState)}`}>
                            {wallDynLabel(wallDynState)}
                        </span>
                    }
                />

                {/* MOMENTUM */}
                <StatCard
                    title="MOMENTUM"
                    badge={
                        <Minus size={14} className="text-text-secondary" />
                    }
                    value={momentumState && momentumState !== 'NEUTRAL' ? momentumState : undefined}
                />

                {/* VANNA */}
                <StatCard
                    title="VANNA"
                    icon={<Zap size={9} className="text-accent-cyan" />}
                    badge={
                        vannaState ? (
                            <span className={`badge ${vannaBadge(vannaState)}`}>
                                {vannaLabel(vannaState)}
                            </span>
                        ) : undefined
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

function wallDynBadge(state: string): string {
    if (state === 'SIEGE') return 'badge-amber'
    if (state === 'RETREAT') return 'badge-red'
    return 'badge-neutral'
}

function wallDynLabel(state: string): string {
    return state || 'STABLE'
}

function vannaBadge(state: string): string {
    if (state === 'CMPRS' || state === 'GRIND_STABLE') return 'badge-cyan'
    if (state === 'DANGER') return 'badge-red'
    if (state === 'FLIP') return 'badge-purple'
    return 'badge-neutral'
}

function vannaLabel(state: string): string {
    const map: Record<string, string> = {
        CMPRS: 'CMPRS',
        GRIND_STABLE: 'CMPRS',
        DANGER: 'DANGER',
        DANGER_ZONE: 'DANGER',
        VANNA_FLIP: 'FLIP',
        FLIP: 'FLIP',
    }
    return map[state] ?? state
}

/**
 * MicroStats — Phase 3: Zustand field-level selector
 *
 * Data source: useDashboardStore(selectMicroStats)
 * Props: kept for backward compat fallback (App.tsx no longer needs to pass them)
 * Layout/DOM/CSS: UNCHANGED
 */
import React, { memo } from 'react'
import { Anchor, Activity, Minus, Zap } from 'lucide-react'
import { useDashboardStore } from '../../store/dashboardStore'

// ─────────────────────────────────────────────────────────────────────────────
// Store selector (field-level — only re-renders when micro_stats changes)
// ─────────────────────────────────────────────────────────────────────────────

const selectMicroStats = (s: ReturnType<typeof useDashboardStore.getState>) =>
    s.payload?.agent_g?.data?.ui_state?.micro_stats ?? null

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface MetricCell {
    label: string
    badge: string
}

interface Props {
    /** Optional override — store value takes priority when available. */
    uiState?: {
        net_gex: MetricCell
        wall_dyn: MetricCell
        vanna: MetricCell
        momentum: MetricCell
    }
}

const ZERO_CELL: MetricCell = { label: '—', badge: 'badge-neutral' }

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components (unchanged)
// ─────────────────────────────────────────────────────────────────────────────

const StatCard: React.FC<{
    title: string
    icon?: React.ReactNode
    badge?: React.ReactNode
    value?: string
}> = ({ title, icon, badge, value }) => (
    <div className="flex flex-col justify-between p-1.5 bg-[#111318] border border-[#1e2025] hover:bg-[#15181e] transition-colors relative overflow-hidden group">
        <div className="flex items-center gap-1.5 opacity-80 mb-1">
            {icon && <span className="opacity-90">{icon}</span>}
            <span className="text-[9px] font-bold text-[#8f939c] uppercase tracking-wider">{title}</span>
        </div>
        <div className="flex items-center justify-end w-full">
            {badge}
            {value && <span className="mono text-[10px] font-bold text-white ml-1">{value}</span>}
        </div>
        {/* Asian-style left edge highlight line */}
        <div className="absolute top-0 left-0 w-[2px] h-full bg-white/5 group-hover:bg-white/20 transition-colors" />
    </div>
)

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export const MicroStats: React.FC<Props> = memo(({ uiState: propUiState }) => {
    // Store selector — fine-grained subscription (only this slice)
    const storeData = useDashboardStore(selectMicroStats)

    // Store takes priority; fall back to prop; then zero-state
    const raw = storeData ?? propUiState ?? null
    const safe = {
        net_gex: raw?.net_gex ?? ZERO_CELL,
        wall_dyn: raw?.wall_dyn ?? ZERO_CELL,
        vanna: raw?.vanna ?? ZERO_CELL,
        momentum: raw?.momentum ?? ZERO_CELL,
    }

    return (
        <div className="p-1 pb-4 space-y-1.5 bg-[#0a0c10]">
            {/* Section title */}
            <div className="flex items-center gap-2 px-1">
                <div className="w-1.5 h-1.5 rounded-sm bg-white/80" />
                <span className="section-header text-white/90 tracking-widest">MICRO STATS</span>
            </div>

            {/* 2×2 grid */}
            <div className="grid grid-cols-2 gap-[2px] px-1">

                {/* NET GEX */}
                <StatCard
                    title="NET GEX"
                    icon={<Activity size={10} className="text-[#a855f7]" />}
                    badge={<span className={`badge ${safe.net_gex.badge}`}>{safe.net_gex.label}</span>}
                />

                {/* WALL DYN */}
                <StatCard
                    title="WALL DYN"
                    icon={<Anchor size={10} className="text-accent-amber" />}
                    badge={<span className={`badge ${safe.wall_dyn.badge}`}>{safe.wall_dyn.label}</span>}
                />

                {/* MOMENTUM */}
                <StatCard
                    title="MOMENTUM"
                    icon={<Minus size={10} className="text-white/60" />}
                    badge={<span className={`badge ${safe.momentum.badge}`}>{safe.momentum.label}</span>}
                />

                {/* VANNA */}
                <StatCard
                    title="VANNA"
                    icon={<Zap size={10} className="text-accent-cyan" />}
                    badge={<span className={`badge ${safe.vanna.badge}`}>{safe.vanna.label}</span>}
                />
            </div>
        </div>
    )
})

MicroStats.displayName = 'MicroStats'

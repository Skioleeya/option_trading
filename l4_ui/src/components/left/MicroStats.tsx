/**
 * MicroStats — Phase 3: Zustand field-level selector
 *
 * Data source: useDashboardStore(selectUiStateMicroStats)
 * Props: kept for backward compat fallback (App.tsx no longer needs to pass them)
 * Layout/DOM/CSS: UNCHANGED
 */
import React, { memo } from 'react'
import { Anchor, Activity, Minus, Zap } from 'lucide-react'
import { useDashboardStore, selectUiStateMicroStats } from '../../store/dashboardStore'
import { MICRO_STATS_THEME, normalizeBadgeToken, normalizeWallDynBadgeToken } from './microStatsTheme'

// ─────────────────────────────────────────────────────────────────────────────
// Store selector (field-level — only re-renders when micro_stats changes)
// ─────────────────────────────────────────────────────────────────────────────

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
    preferProp?: boolean
}

const MICRO_STATS_UI = {
    emptyLabel: '—',
    iconSize: 10,
    neutralBadge: 'badge-neutral',
} as const

const ZERO_CELL: MetricCell = { label: MICRO_STATS_UI.emptyLabel, badge: MICRO_STATS_UI.neutralBadge }

const normalizeCell = (cell?: MetricCell | null): MetricCell => ({
    label: cell?.label ?? MICRO_STATS_UI.emptyLabel,
    badge: normalizeBadgeToken(cell?.badge, cell?.label),
})

const normalizeWallDynCell = (cell?: MetricCell | null): MetricCell => ({
    label: cell?.label ?? MICRO_STATS_UI.emptyLabel,
    badge: normalizeWallDynBadgeToken(cell?.badge, cell?.label),
})

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components (unchanged)
// ─────────────────────────────────────────────────────────────────────────────

const StatCard: React.FC<{
    title: string
    icon?: React.ReactNode
    badge?: React.ReactNode
    value?: string
}> = ({ title, icon, badge, value }) => (
    <div
        className="flex flex-col justify-between p-1.5 border transition-colors relative overflow-hidden group hover:bg-[var(--ms-card-hover)]"
        style={{
            backgroundColor: MICRO_STATS_THEME.cardBg,
            borderColor: MICRO_STATS_THEME.cardBorder,
            ['--ms-card-hover' as string]: MICRO_STATS_THEME.cardHoverBg,
            ['--ms-edge-idle' as string]: MICRO_STATS_THEME.edgeIdle,
            ['--ms-edge-hover' as string]: MICRO_STATS_THEME.edgeHover,
        } as React.CSSProperties}
    >
        <div className="flex items-center gap-1.5 opacity-80 mb-1">
            {icon && <span className="opacity-90">{icon}</span>}
            <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: MICRO_STATS_THEME.title }}>{title}</span>
        </div>
        <div className="flex items-center justify-end w-full">
            {badge}
            {value && <span className="mono text-[10px] font-bold text-white ml-1">{value}</span>}
        </div>
        {/* Asian-style left edge highlight line */}
        <div className="absolute top-0 left-0 w-[2px] h-full bg-[var(--ms-edge-idle)] group-hover:bg-[var(--ms-edge-hover)] transition-colors" />
    </div>
)

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export const MicroStats: React.FC<Props> = memo(({ uiState: propUiState, preferProp = false }) => {
    // Store selector — fine-grained subscription (only this slice)
    const storeData = useDashboardStore(selectUiStateMicroStats)

    // Store takes priority; fall back to prop; then zero-state
    const raw = preferProp
        ? (propUiState ?? storeData ?? null)
        : (storeData ?? propUiState ?? null)
    const safe = {
        net_gex: normalizeCell(raw?.net_gex ?? ZERO_CELL),
        wall_dyn: normalizeWallDynCell(raw?.wall_dyn ?? ZERO_CELL),
        vanna: normalizeCell(raw?.vanna ?? ZERO_CELL),
        momentum: normalizeCell(raw?.momentum ?? ZERO_CELL),
    }

    return (
        <div className="p-1 pb-4 space-y-1.5" style={{ backgroundColor: MICRO_STATS_THEME.panelBg }}>
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
                    icon={<Activity size={MICRO_STATS_UI.iconSize} style={{ color: MICRO_STATS_THEME.icons.netGex }} />}
                    badge={<span className={`badge ${safe.net_gex.badge}`}>{safe.net_gex.label}</span>}
                />

                {/* WALL DYN */}
                <StatCard
                    title="WALL DYN"
                    icon={<Anchor size={MICRO_STATS_UI.iconSize} style={{ color: MICRO_STATS_THEME.icons.wallDyn }} />}
                    badge={<span className={`badge ${safe.wall_dyn.badge}`}>{safe.wall_dyn.label}</span>}
                />

                {/* MOMENTUM */}
                <StatCard
                    title="MOMENTUM"
                    icon={<Minus size={MICRO_STATS_UI.iconSize} style={{ color: MICRO_STATS_THEME.icons.momentum }} />}
                    badge={<span className={`badge ${safe.momentum.badge}`}>{safe.momentum.label}</span>}
                />

                {/* VANNA */}
                <StatCard
                    title="VANNA"
                    icon={<Zap size={MICRO_STATS_UI.iconSize} style={{ color: MICRO_STATS_THEME.icons.vanna }} />}
                    badge={<span className={`badge ${safe.vanna.badge}`}>{safe.vanna.label}</span>}
                />
            </div>
        </div>
    )
})

MicroStats.displayName = 'MicroStats'

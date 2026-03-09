import { THEME } from '../../lib/theme'

const LEGACY_BADGE_ALIASES: Record<string, string> = {
    positive: 'badge-red',
    negative: 'badge-green',
    neutral: 'badge-neutral',
    warning: 'badge-amber',
    danger: 'badge-red',
    'badge-positive': 'badge-red',
    'badge-negative': 'badge-green',
    'badge-warning': 'badge-amber',
    'badge-danger': 'badge-red',
    'badge-super-pin': 'badge-amber',
    'badge-damping': 'badge-hollow-green',
    'badge-acceleration': 'badge-hollow-purple',
}

export function normalizeBadgeToken(raw: string | null | undefined): string {
    const token = String(raw ?? '').trim()
    if (!token) return 'badge-neutral'
    return LEGACY_BADGE_ALIASES[token] ?? token
}

export const MICRO_STATS_THEME = {
    panelBg: THEME.defense.microStats.panelBg,
    cardBg: THEME.defense.microStats.cardBg,
    cardBorder: THEME.defense.microStats.cardBorder,
    cardHoverBg: THEME.defense.microStats.cardHoverBg,
    title: THEME.defense.microStats.title,
    edgeIdle: THEME.defense.microStats.edgeIdle,
    edgeHover: THEME.defense.microStats.edgeHover,
    icons: {
        netGex: THEME.defense.microStats.iconNetGex,
        wallDyn: THEME.defense.microStats.iconWallDyn,
        momentum: THEME.defense.microStats.iconMomentum,
        vanna: THEME.defense.microStats.iconVanna,
    },
} as const

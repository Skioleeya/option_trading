import { THEME } from '../../lib/theme'

const LEGACY_BADGE_ALIASES: Record<string, string> = {
    positive: 'badge-red',
    negative: 'badge-green',
    bullish: 'badge-red',
    bearish: 'badge-green',
    neutral: 'badge-neutral',
    warning: 'badge-amber',
    danger: 'badge-red',
    'badge-positive': 'badge-red',
    'badge-negative': 'badge-green',
    'badge-bullish': 'badge-red',
    'badge-bearish': 'badge-green',
    'badge-warning': 'badge-amber',
    'badge-danger': 'badge-red',
    'badge-super-pin': 'badge-amber',
    'badge-damping': 'badge-hollow-green',
    'badge-acceleration': 'badge-red-dim',
}

export function normalizeBadgeToken(raw: string | null | undefined, label?: string | null): string {
    const token = String(raw ?? '').trim()
    const mapped = token ? (LEGACY_BADGE_ALIASES[token] ?? token) : ''
    if (mapped) return mapped

    const normalizedLabel = String(label ?? '').toUpperCase()
    if (normalizedLabel.includes('BULL') || normalizedLabel.includes('UP') || normalizedLabel.includes('LONG')) {
        return 'badge-red'
    }
    if (normalizedLabel.includes('BEAR') || normalizedLabel.includes('DOWN') || normalizedLabel.includes('SHORT')) {
        return 'badge-green'
    }
    return 'badge-neutral'
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
        netGex: THEME.market.up,
        wallDyn: THEME.market.down,
        momentum: THEME.defense.microStats.iconMomentum,
        vanna: THEME.defense.microStats.iconVanna,
    },
} as const

import { THEME } from '../../lib/theme'

const BADGE = {
    RED: 'badge-red',
    GREEN: 'badge-green',
    AMBER: 'badge-amber',
    NEUTRAL: 'badge-neutral',
    HOLLOW_GREEN: 'badge-hollow-green',
    RED_DIM: 'badge-red-dim',
} as const

const DIRECTION_UP_KEYWORDS = ['CALL', 'BULL', 'UP', 'LONG', '↑'] as const
const DIRECTION_DOWN_KEYWORDS = ['PUT', 'BEAR', 'DOWN', 'SHORT', '↓'] as const

const STATE_DECAY = 'DECAY'
const STATE_REINFORCE = 'REINFORCE'

const LEGACY_BADGE_ALIASES: Record<string, string> = {
    positive: BADGE.RED,
    negative: BADGE.GREEN,
    bullish: BADGE.RED,
    bearish: BADGE.GREEN,
    neutral: BADGE.NEUTRAL,
    warning: BADGE.AMBER,
    danger: BADGE.RED,
    'badge-positive': BADGE.RED,
    'badge-negative': BADGE.GREEN,
    'badge-bullish': BADGE.RED,
    'badge-bearish': BADGE.GREEN,
    'badge-warning': BADGE.AMBER,
    'badge-danger': BADGE.RED,
    'badge-super-pin': BADGE.AMBER,
    'badge-damping': BADGE.HOLLOW_GREEN,
    'badge-acceleration': BADGE.RED_DIM,
}

const WALL_DYN_NOISE_STATES = ['SIEGE', 'PINCH', 'STABLE', 'UNAVAILABLE']
const WALL_DYN_RISK_STATES = ['COLLAPSE', 'RETREAT', 'BREACH']

function normalizeStateToken(raw: unknown): string {
    const text = String(raw ?? '').trim().toUpperCase()
    return text ? text.replace(/\s+/g, ' ') : ''
}

function hasAnyKeyword(text: string, keywords: readonly string[]): boolean {
    return keywords.some((keyword) => text.includes(keyword))
}

export function normalizeBadgeToken(raw: string | null | undefined, label?: string | null): string {
    const token = String(raw ?? '').trim()
    const mapped = token ? (LEGACY_BADGE_ALIASES[token] ?? token) : ''
    if (mapped) return mapped

    const normalizedLabel = String(label ?? '').toUpperCase()
    if (hasAnyKeyword(normalizedLabel, DIRECTION_UP_KEYWORDS)) {
        return BADGE.RED
    }
    if (hasAnyKeyword(normalizedLabel, DIRECTION_DOWN_KEYWORDS)) {
        return BADGE.GREEN
    }
    return BADGE.NEUTRAL
}

export function normalizeWallDynBadgeToken(raw: string | null | undefined, label?: string | null): string {
    const normalizedLabel = normalizeStateToken(label)

    // Hard-cut governance: wall_dyn no longer inherits backend badge token.
    // Only whitelist state semantics can drive the color.
    if (hasAnyKeyword(normalizedLabel, WALL_DYN_RISK_STATES)) {
        return BADGE.AMBER
    }
    if (normalizedLabel.includes(STATE_DECAY)) {
        return BADGE.NEUTRAL
    }
    if (WALL_DYN_NOISE_STATES.some((state) => normalizedLabel.includes(state))) {
        return BADGE.NEUTRAL
    }
    if (normalizedLabel.includes(STATE_REINFORCE)) {
        if (hasAnyKeyword(normalizedLabel, DIRECTION_UP_KEYWORDS)) {
            return BADGE.RED
        }
        if (hasAnyKeyword(normalizedLabel, DIRECTION_DOWN_KEYWORDS)) {
            return BADGE.GREEN
        }
        return BADGE.NEUTRAL
    }

    // Unknown or future labels must stay neutral until explicitly mapped.
    // `raw` is intentionally ignored to prevent reverse color semantics drift.
    void raw
    return BADGE.NEUTRAL
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
        wallDyn: THEME.defense.microStats.iconWallDyn,
        momentum: THEME.defense.microStats.iconMomentum,
        vanna: THEME.defense.microStats.iconVanna,
    },
} as const

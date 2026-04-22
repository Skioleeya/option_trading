import { THEME } from '../../lib/theme'

export interface WallMigrationRowLike {
    label?: string | null
    state?: string | null
    lights?: Record<string, string> | null
}

export interface WallMigrationRowTokens {
    isCall: boolean
    state: string
    isBreached: boolean
    isDecaying: boolean
    isReinforced: boolean
    isRetreating: boolean
    isCollapsing: boolean
    labelColor: string
    labelBorder: string
    labelBg: string
    badgeColor: string
    retreatColor: string
    currentBorder: string
    currentBg: string
    currentShadow: string
}

function hexToRgbTriplet(hex: string, fallback: string): string {
    const normalized = hex.trim().replace('#', '')
    if (!/^[0-9a-fA-F]{6}$/.test(normalized)) return fallback
    const r = Number.parseInt(normalized.slice(0, 2), 16)
    const g = Number.parseInt(normalized.slice(2, 4), 16)
    const b = Number.parseInt(normalized.slice(4, 6), 16)
    return `${r},${g},${b}`
}

const WALL_LEVEL_MIN_EXCLUSIVE = 0

function normalizeStateToken(raw: unknown): string {
    const text = String(raw ?? '').trim().toUpperCase()
    return text ? text.replace(/\s+/g, ' ') : ''
}

function hasState(state: string, keyword: string): boolean {
    return state.includes(keyword)
}

export function isDisplayableWallLevel(value: unknown): value is number {
    return typeof value === 'number' && Number.isFinite(value) && value > WALL_LEVEL_MIN_EXCLUSIVE
}

export function getHistoryValue(history: unknown, index: number): number | null {
    if (!Array.isArray(history) || index < 0 || index >= history.length) {
        return null
    }
    const value = history[index]
    return isDisplayableWallLevel(value) ? value : null
}

export function getWallMigrationRowTokens(row: WallMigrationRowLike): WallMigrationRowTokens {
    const label = String(row.label ?? '').toUpperCase()
    const stateCandidate = normalizeStateToken(row.state)
    const badgeCandidate = normalizeStateToken(row.lights?.wall_dyn_badge)
    const state = stateCandidate || badgeCandidate || 'UNAVAILABLE'

    const isCall = label.startsWith('C') || label.includes('CALL')
    const isPut = label.startsWith('P') || label.includes('PUT')
    const isBreached = hasState(state, 'BREACH')
    const isDecaying = hasState(state, 'DECAY')
    const isReinforced = hasState(state, 'REINFORCE')
    const isRetreating = hasState(state, 'RETREAT')
    const isCollapsing = hasState(state, 'COLLAPSE')

    const marketUpRgb = hexToRgbTriplet(THEME.market.up, '239,68,68')
    const marketDownRgb = hexToRgbTriplet(THEME.market.down, '16,185,129')
    const labelColor = isCall ? THEME.market.up : isPut ? THEME.market.down : THEME.text.secondary
    const labelBorder = isCall
        ? `rgba(${marketUpRgb},0.30)`
        : isPut
            ? `rgba(${marketDownRgb},0.30)`
            : 'rgba(255,255,255,0.20)'
    const labelBg = isCall
        ? THEME.defense.wallMigration.callLabelBg
        : isPut
            ? THEME.defense.wallMigration.putLabelBg
            : 'rgba(18,18,20,0.80)'

    const neutralBorder = 'rgba(255,255,255,0.10)'
    const neutralBg = 'rgba(18,18,20,0.80)'
    const neutralShadow = 'none'

    const retreatBorder = 'rgba(245,158,11,0.45)'
    const retreatBg = 'rgba(245,158,11,0.08)'
    const retreatShadow = '0 0 6px rgba(245,158,11,0.25)'

    const reinforceBorder = isCall
        ? `rgba(${marketUpRgb},0.45)`
        : isPut
            ? `rgba(${marketDownRgb},0.45)`
            : 'rgba(255,255,255,0.24)'
    const reinforceBg = isCall
        ? `rgba(${marketUpRgb},0.12)`
        : isPut
            ? `rgba(${marketDownRgb},0.12)`
            : 'rgba(255,255,255,0.06)'
    const reinforceShadow = isCall
        ? `0 0 8px rgba(${marketUpRgb},0.30)`
        : isPut
            ? `0 0 8px rgba(${marketDownRgb},0.30)`
            : 'none'

    const breachBorder = 'rgba(245,158,11,0.6)'
    const breachBg = 'rgba(245,158,11,0.14)'
    const breachShadow = '0 0 8px rgba(245,158,11,0.35)'
    const collapseBorder = 'rgba(245,158,11,0.75)'
    const collapseBg = 'rgba(245,158,11,0.18)'
    const collapseShadow = '0 0 10px rgba(245,158,11,0.45)'

    const decayingBorder = 'rgba(113,113,122,0.25)'
    const decayingBg = '#060606'
    const decayingShadow = 'none'

    const badgeColor = (isBreached || isCollapsing)
        ? THEME.accent.amber
        : isReinforced
            ? (isCall ? THEME.market.up : isPut ? THEME.market.down : THEME.text.secondary)
            : isRetreating
                ? THEME.accent.amber
                : isDecaying
                    ? THEME.text.secondary
                    : THEME.text.secondary

    let currentBorder = neutralBorder
    let currentBg = neutralBg
    let currentShadow = neutralShadow

    if (isDecaying) {
        currentBorder = decayingBorder
        currentBg = decayingBg
        currentShadow = decayingShadow
    } else if (isBreached || isCollapsing) {
        currentBorder = isCollapsing ? collapseBorder : breachBorder
        currentBg = isCollapsing ? collapseBg : breachBg
        currentShadow = isCollapsing ? collapseShadow : breachShadow
    } else if (isReinforced) {
        currentBorder = reinforceBorder
        currentBg = reinforceBg
        currentShadow = reinforceShadow
    } else if (isRetreating) {
        currentBorder = retreatBorder
        currentBg = retreatBg
        currentShadow = retreatShadow
    }

    return {
        isCall,
        state,
        isBreached,
        isDecaying,
        isReinforced,
        isRetreating,
        isCollapsing,
        labelColor,
        labelBorder,
        labelBg,
        badgeColor,
        retreatColor: THEME.accent.amber,
        currentBorder,
        currentBg,
        currentShadow,
    }
}

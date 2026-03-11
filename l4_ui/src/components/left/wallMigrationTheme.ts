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
    labelColor: string
    labelBorder: string
    labelBg: string
    badgeColor: string
    retreatColor: string
    currentBorder: string
    currentBg: string
    currentShadow: string
}

export function getHistoryValue(history: unknown, index: number): number | null {
    if (!Array.isArray(history) || index < 0 || index >= history.length) {
        return null
    }
    const value = history[index]
    return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function getWallMigrationRowTokens(row: WallMigrationRowLike): WallMigrationRowTokens {
    const label = String(row.label ?? '').toUpperCase()
    const state = String(row.state ?? 'UNAVAILABLE').toUpperCase()

    const isCall = label.startsWith('C')
    const isBreached = state.includes('BREACHED')
    const isDecaying = state.includes('DECAYING')
    const isReinforced = state.includes('REINFORCED')
    const isRetreating = state.includes('RETREATING')

    const labelColor = isCall ? THEME.market.up : THEME.market.down
    const labelBorder = isCall ? 'rgba(239,68,68,0.30)' : 'rgba(16,185,129,0.30)'
    const labelBg = isCall
        ? THEME.defense.wallMigration.callLabelBg
        : THEME.defense.wallMigration.putLabelBg

    const neutralBorder = 'rgba(255,255,255,0.10)'
    const neutralBg = 'rgba(18,18,20,0.80)'
    const neutralShadow = 'none'

    const retreatBorder = 'rgba(245,158,11,0.45)'
    const retreatBg = 'rgba(245,158,11,0.08)'
    const retreatShadow = '0 0 6px rgba(245,158,11,0.25)'

    const reinforceBorder = isCall ? 'rgba(239,68,68,0.45)' : 'rgba(16,185,129,0.45)'
    const reinforceBg = isCall ? 'rgba(239,68,68,0.12)' : 'rgba(16,185,129,0.12)'
    const reinforceShadow = isCall
        ? '0 0 8px rgba(239,68,68,0.30)'
        : '0 0 8px rgba(16,185,129,0.30)'

    const breachBorder = 'rgba(245,158,11,0.6)'
    const breachBg = 'rgba(245,158,11,0.14)'
    const breachShadow = '0 0 8px rgba(245,158,11,0.35)'

    const decayingBorder = 'rgba(113,113,122,0.25)'
    const decayingBg = '#060606'
    const decayingShadow = 'none'

    const badgeColor = isBreached
        ? THEME.accent.amber
        : isReinforced
            ? (isCall ? THEME.market.up : THEME.market.down)
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
    } else if (isBreached) {
        currentBorder = breachBorder
        currentBg = breachBg
        currentShadow = breachShadow
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

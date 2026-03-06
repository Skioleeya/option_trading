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
    const lights = row.lights ?? {}

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
        badgeColor: lights.wall_dyn_color || THEME.text.secondary,
        retreatColor: THEME.accent.amber,
        currentBorder: lights.current_border || 'rgba(255,255,255,0.10)',
        currentBg: lights.current_bg || (isDecaying ? '#060606' : 'rgba(18,18,20,0.80)'),
        currentShadow: lights.current_shadow || 'none',
    }
}

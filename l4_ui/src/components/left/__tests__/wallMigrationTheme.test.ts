import { describe, expect, it } from 'vitest'
import { getHistoryValue, getWallMigrationRowTokens, isDisplayableWallLevel } from '../wallMigrationTheme'

describe('wallMigrationTheme', () => {
    it('treats invalid state as safe fallback', () => {
        const tokens = getWallMigrationRowTokens({
            label: 'C',
            state: null,
            lights: null,
        })

        expect(tokens.state).toBe('UNAVAILABLE')
        expect(tokens.isBreached).toBe(false)
        expect(tokens.labelColor).toBe('#ef4444')
    })

    it('preserves asian style direction colors', () => {
        const call = getWallMigrationRowTokens({ label: 'C', state: 'STABLE', lights: {} })
        const put = getWallMigrationRowTokens({ label: 'P', state: 'STABLE', lights: {} })

        expect(call.labelColor).toBe('#ef4444')
        expect(put.labelColor).toBe('#10b981')
    })

    it('keeps unknown wall labels neutral instead of forcing put semantics', () => {
        const unknown = getWallMigrationRowTokens({ label: 'UNKNOWN', state: 'REINFORCED', lights: {} })
        expect(unknown.labelColor).toBe('#71717a')
        expect(unknown.badgeColor).toBe('#71717a')
    })

    it('returns finite positive history value only', () => {
        expect(getHistoryValue([565, 560], 0)).toBe(565)
        expect(getHistoryValue([0, 565], 0)).toBeNull()
        expect(getHistoryValue([-1, 565], 0)).toBeNull()
        expect(getHistoryValue([565, NaN], 1)).toBeNull()
        expect(getHistoryValue(undefined, 0)).toBeNull()
    })

    it('normalizes RETREAT and COLLAPSE state variants for color management', () => {
        const retreat = getWallMigrationRowTokens({ label: 'PUT WALL', state: 'RETREAT ↓', lights: {} })
        const collapse = getWallMigrationRowTokens({ label: 'PUT WALL', state: 'COLLAPSE', lights: {} })

        expect(retreat.isRetreating).toBe(true)
        expect(collapse.isCollapsing).toBe(true)
        expect(collapse.badgeColor).toBe('#f59e0b')
    })

    it('shares a single wall level threshold helper', () => {
        expect(isDisplayableWallLevel(560)).toBe(true)
        expect(isDisplayableWallLevel(0)).toBe(false)
        expect(isDisplayableWallLevel(-5)).toBe(false)
        expect(isDisplayableWallLevel(Number.NaN)).toBe(false)
    })

    it('ignores backend style injection and keeps local visual mapping', () => {
        const tokens = getWallMigrationRowTokens({
            label: 'C',
            state: 'REINFORCED',
            lights: {
                wall_dyn_color: '#000000',
                current_border: '#000000',
                current_bg: '#000000',
                current_shadow: '0 0 0 #000000',
            },
        })

        expect(tokens.badgeColor).toBe('#ef4444')
        expect(tokens.currentBorder).toContain('239,68,68')
        expect(tokens.currentBg).toContain('239,68,68')
        expect(tokens.currentShadow).toContain('239,68,68')
    })
})

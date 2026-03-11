import { describe, expect, it } from 'vitest'
import { getHistoryValue, getWallMigrationRowTokens } from '../wallMigrationTheme'

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

    it('returns finite history value only', () => {
        expect(getHistoryValue([565, 560], 0)).toBe(565)
        expect(getHistoryValue([565, NaN], 1)).toBeNull()
        expect(getHistoryValue(undefined, 0)).toBeNull()
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

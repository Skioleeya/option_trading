import { describe, expect, it } from 'vitest'
import { MICRO_STATS_THEME, normalizeBadgeToken } from '../microStatsTheme'

describe('microStatsTheme', () => {
    it('normalizes legacy badge tokens to canonical classes', () => {
        expect(normalizeBadgeToken('badge-positive')).toBe('badge-red')
        expect(normalizeBadgeToken('badge-negative')).toBe('badge-green')
        expect(normalizeBadgeToken('badge-warning')).toBe('badge-amber')
        expect(normalizeBadgeToken('badge-danger')).toBe('badge-red')
    })

    it('returns safe neutral when badge is missing', () => {
        expect(normalizeBadgeToken(undefined)).toBe('badge-neutral')
        expect(normalizeBadgeToken('')).toBe('badge-neutral')
    })

    it('exposes Asian Dragon icon/theme tokens', () => {
        expect(MICRO_STATS_THEME.icons.netGex).toBe('#a855f7')
        expect(MICRO_STATS_THEME.icons.wallDyn).toBe('#f59e0b')
        expect(MICRO_STATS_THEME.cardBg).toBe('#111318')
    })
})

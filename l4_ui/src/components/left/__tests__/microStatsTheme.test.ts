import { describe, expect, it } from 'vitest'
import { MICRO_STATS_THEME, normalizeBadgeToken } from '../microStatsTheme'

describe('microStatsTheme', () => {
    it('normalizes legacy badge tokens to canonical classes', () => {
        expect(normalizeBadgeToken('badge-positive')).toBe('badge-red')
        expect(normalizeBadgeToken('badge-negative')).toBe('badge-green')
        expect(normalizeBadgeToken('badge-warning')).toBe('badge-amber')
        expect(normalizeBadgeToken('badge-danger')).toBe('badge-red')
        expect(normalizeBadgeToken('badge-acceleration')).toBe('badge-red-dim')
    })

    it('returns safe neutral when badge is missing', () => {
        expect(normalizeBadgeToken(undefined)).toBe('badge-neutral')
        expect(normalizeBadgeToken('')).toBe('badge-neutral')
    })

    it('infers asian badge direction from label when token is absent', () => {
        expect(normalizeBadgeToken('', 'bull breakout')).toBe('badge-red')
        expect(normalizeBadgeToken('', 'bear breakdown')).toBe('badge-green')
    })

    it('exposes Asian Dragon icon/theme tokens', () => {
        expect(MICRO_STATS_THEME.icons.netGex).toBe('#ef4444')
        expect(MICRO_STATS_THEME.icons.wallDyn).toBe('#10b981')
        expect(MICRO_STATS_THEME.cardBg).toBe('#111318')
    })
})

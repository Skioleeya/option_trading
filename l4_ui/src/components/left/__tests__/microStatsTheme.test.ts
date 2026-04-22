import { describe, expect, it } from 'vitest'
import { MICRO_STATS_THEME, normalizeBadgeToken, normalizeWallDynBadgeToken } from '../microStatsTheme'

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

    it('normalizes WALL DYN risk/noise states to match wall migration semantics', () => {
        expect(normalizeWallDynBadgeToken('badge-red', 'RETREAT ↑')).toBe('badge-amber')
        expect(normalizeWallDynBadgeToken('badge-red', 'COLLAPSE')).toBe('badge-amber')
        expect(normalizeWallDynBadgeToken('badge-red', 'BREACH')).toBe('badge-amber')
        expect(normalizeWallDynBadgeToken('badge-red', 'DECAYING')).toBe('badge-neutral')
        expect(normalizeWallDynBadgeToken('badge-red', 'SIEGE')).toBe('badge-neutral')
    })

    it('maps WALL DYN reinforced direction to asian red/green semantics', () => {
        expect(normalizeWallDynBadgeToken('badge-neutral', 'REINFORCED CALL')).toBe('badge-red')
        expect(normalizeWallDynBadgeToken('badge-neutral', 'REINFORCED PUT')).toBe('badge-green')
    })

    it('hard-cuts WALL DYN unknown states to neutral and ignores backend badge token', () => {
        expect(normalizeWallDynBadgeToken('badge-red', 'NEW_STATE_X')).toBe('badge-neutral')
        expect(normalizeWallDynBadgeToken('badge-green', '')).toBe('badge-neutral')
    })

    it('exposes Asian Dragon icon/theme tokens', () => {
        expect(MICRO_STATS_THEME.icons.netGex).toBe('#ef4444')
        expect(MICRO_STATS_THEME.icons.wallDyn).toBe('#f59e0b')
        expect(MICRO_STATS_THEME.cardBg).toBe('#111318')
    })
})


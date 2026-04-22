import { describe, expect, it } from 'vitest'
import { normalizeBadgeToken, normalizeWallDynBadgeToken } from '../microStatsTheme'

describe('microStatsTheme', () => {
    it('maps directional labels to strict red and green badge tokens', () => {
        expect(normalizeBadgeToken(undefined, 'CALL LADDER')).toBe('badge-red')
        expect(normalizeBadgeToken(undefined, 'SHORT')).toBe('badge-green')
        expect(normalizeBadgeToken('badge-warning', 'ignored')).toBe('badge-amber')
    })

    it('maps wall-dyn risk states by label and ignores backend badge color drift', () => {
        expect(normalizeWallDynBadgeToken('badge-red', 'BREACH ↓')).toBe('badge-amber')
        expect(normalizeWallDynBadgeToken('badge-green', 'REINFORCE CALL')).toBe('badge-red')
        expect(normalizeWallDynBadgeToken('badge-red', 'REINFORCE PUT')).toBe('badge-green')
        expect(normalizeWallDynBadgeToken('badge-red', 'STABLE')).toBe('badge-neutral')
    })

    it('hard-cuts unknown wall-dyn labels to neutral', () => {
        expect(normalizeWallDynBadgeToken('badge-red', 'CUSTOM SIGNAL')).toBe('badge-neutral')
    })
})

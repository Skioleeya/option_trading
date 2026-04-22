import { describe, expect, it } from 'vitest'
import { DEPTH_PROFILE_THEME } from '../depthProfileTheme'

describe('depthProfileTheme', () => {
    it('keeps put direction on green gradient classes', () => {
        expect(DEPTH_PROFILE_THEME.putDominantBarClass).toContain('#10b981')
        expect(DEPTH_PROFILE_THEME.putNormalBarClass).toContain('#10b981')
        expect(DEPTH_PROFILE_THEME.putDominantBarClass).not.toContain('#ef4444')
    })

    it('keeps call direction on red gradient classes', () => {
        expect(DEPTH_PROFILE_THEME.callDominantBarClass).toContain('#ef4444')
        expect(DEPTH_PROFILE_THEME.callNormalBarClass).toContain('#ef4444')
        expect(DEPTH_PROFILE_THEME.callDominantBarClass).not.toContain('#10b981')
    })
})

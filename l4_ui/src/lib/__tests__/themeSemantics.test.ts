import { describe, expect, it } from 'vitest'
import { THEME } from '../theme'

describe('theme semantic colors', () => {
    it('keeps asian directional mapping fixed', () => {
        expect(THEME.market.up).toBe('#ef4444')
        expect(THEME.market.down).toBe('#10b981')
    })

    it('aligns accent red/green with market up/down to prevent semantic drift', () => {
        expect(THEME.accent.red).toBe(THEME.market.up)
        expect(THEME.accent.green).toBe(THEME.market.down)
    })

    it('keeps wall and chart call/put directional colors consistent with market tokens', () => {
        expect(THEME.defense.depthProfile.callBar).toBe(THEME.market.up)
        expect(THEME.defense.depthProfile.putBar).toBe(THEME.market.down)
        expect(THEME.chart.candlestick.upColor).toBe(THEME.market.up)
        expect(THEME.chart.candlestick.downColor).toBe(THEME.market.down)
    })
})

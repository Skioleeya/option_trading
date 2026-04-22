import { describe, expect, it } from 'vitest'
import {
    buildLayoutScaleVars,
    clampLayoutScale,
    computeLayoutScale,
    L4_LAYOUT_MAX_SCALE,
    L4_LAYOUT_MIN_SCALE,
    resolveLayoutProfile,
} from '../layoutScale'

describe('layoutScale', () => {
    it('computes 100 percent at the design baseline', () => {
        expect(computeLayoutScale({ width: 1920, height: 1080 })).toEqual({
            scale: 1,
            percent: 100,
            profile: 'primary_standard',
        })
    })

    it('uses min width and height ratio with lower clamp', () => {
        expect(computeLayoutScale({ width: 900, height: 760 })).toEqual({
            scale: L4_LAYOUT_MIN_SCALE,
            percent: 50,
            profile: 'secondary_compact',
        })
    })

    it('applies upper clamp at 125 percent', () => {
        expect(computeLayoutScale({ width: 3000, height: 3000 })).toEqual({
            scale: L4_LAYOUT_MAX_SCALE,
            percent: 125,
            profile: 'primary_standard',
        })
    })

    it('resolves primary and secondary viewport profiles', () => {
        expect(resolveLayoutProfile({ width: 1536, height: 864 })).toBe('primary_standard')
        expect(resolveLayoutProfile({ width: 1366, height: 768 })).toBe('secondary_compact')
        expect(resolveLayoutProfile({ width: 1280, height: 720 })).toBe('secondary_compact')
    })

    it('builds primary profile variables from profile and scale', () => {
        expect(buildLayoutScaleVars(0.8, 'primary_standard')).toMatchObject({
            '--l4-left-w': '272px',
            '--l4-right-w': '296px',
            '--l4-header-h': '36px',
            '--l4-header-title-font': '11px',
            '--l4-header-meta-font': '10px',
            '--l4-header-title-line-h': '13px',
            '--l4-header-cluster-gap': '12px',
            '--l4-gex-bar-w': '520px',
            '--l4-panel-pad': '8px',
        })
    })

    it('builds secondary profile variables from profile and scale', () => {
        expect(buildLayoutScaleVars(0.51, 'secondary_compact')).toMatchObject({
            '--l4-left-w': '240px',
            '--l4-right-w': '264px',
            '--l4-header-h': '34px',
            '--l4-header-title-font': '10px',
            '--l4-header-meta-font': '9px',
            '--l4-header-micro-font': '7px',
            '--l4-header-micro-line-h': '8px',
            '--l4-header-gap': '10px',
            '--l4-header-cluster-gap': '8px',
            '--l4-gex-bar-w': '440px',
            '--l4-panel-pad': '5px',
        })
    })

    it('clamps arbitrary scale inputs into the supported range', () => {
        expect(clampLayoutScale(0.2)).toBe(L4_LAYOUT_MIN_SCALE)
        expect(clampLayoutScale(2)).toBe(L4_LAYOUT_MAX_SCALE)
    })
})

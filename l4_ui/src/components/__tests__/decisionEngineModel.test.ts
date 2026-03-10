import { describe, expect, it } from 'vitest'
import type { FusedSignal } from '../../types/dashboard'
import {
    confidenceToPercent,
    formatRegimeLabel,
    normalizeDecisionTone,
    resolveDirectionClasses,
    resolveGexIntensityBadgeClass,
    resolveWeightBarWidth,
    resolveWeightPercent,
} from '../right/decisionEngineModel'

function makeFused(partial?: Partial<FusedSignal>): FusedSignal {
    return {
        direction: 'NEUTRAL',
        confidence: 0,
        weights: {},
        regime: 'NORMAL',
        iv_regime: 'NORMAL',
        gex_intensity: 'NEUTRAL',
        explanation: '',
        components: {},
        ...partial,
    }
}

describe('decisionEngineModel', () => {
    it('normalizes HALT and IV regime aliases to supported tones', () => {
        expect(normalizeDecisionTone('HALT')).toBe('HALT')
        expect(normalizeDecisionTone('LOW_VOL')).toBe('BULLISH')
        expect(normalizeDecisionTone('HIGH_VOL')).toBe('BEARISH')
        expect(normalizeDecisionTone('unknown')).toBe('NEUTRAL')
    })

    it('clamps confidence percent to a valid range', () => {
        expect(confidenceToPercent(0.256)).toBe(26)
        expect(confidenceToPercent(1.2)).toBe(100)
        expect(confidenceToPercent(-0.3)).toBe(0)
    })

    it('resolves quadrant weights from fused weights first, then component weight', () => {
        const fromWeights = makeFused({
            weights: { momentum_signal: 0.31 },
            components: { momentum_signal: { direction: 'BULLISH', confidence: 0.8 } },
        })
        expect(resolveWeightPercent(fromWeights, 'momentum_signal')).toBe(31)

        const fromComponent = makeFused({
            weights: {},
            components: { flow_analyzer: { direction: 'BEARISH', confidence: 0.7, weight: 0.27 } },
        })
        expect(resolveWeightPercent(fromComponent, 'flow_analyzer')).toBe(27)
    })

    it('maps gex intensity to stable badge classes', () => {
        expect(resolveGexIntensityBadgeClass('EXTREME_NEGATIVE')).toBe('badge-hollow-purple')
        expect(resolveGexIntensityBadgeClass('STRONG_POSITIVE')).toBe('badge-hollow-green')
        expect(resolveGexIntensityBadgeClass('EXTREME_POSITIVE')).toBe('badge-amber')
        expect(resolveGexIntensityBadgeClass('MODERATE')).toBe('badge-neutral')
        expect(resolveGexIntensityBadgeClass('NEUTRAL')).toBe('badge-neutral')
    })

    it('keeps zero-weight bars hidden and preserves HALT styling', () => {
        expect(resolveWeightBarWidth(0)).toBe(0)
        expect(resolveWeightBarWidth(1)).toBe(2)
        expect(resolveWeightBarWidth(25)).toBe(25)
        expect(resolveDirectionClasses('HALT').bar).toContain('accent-amber')
    })

    it('formats regime labels without per-letter splitting', () => {
        expect(formatRegimeLabel('NEUTRAL')).toBe('NEUTRAL')
        expect(formatRegimeLabel('EXTREME_NEGATIVE')).toBe('EXTREME NEGATIVE')
        expect(formatRegimeLabel('HighVol')).toBe('HIGH VOL')
    })
})

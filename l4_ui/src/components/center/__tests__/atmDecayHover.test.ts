import { describe, expect, it } from 'vitest'
import type { MouseEventParams, Time } from 'lightweight-charts'
import {
    buildSeriesVisualState,
    hasValidCrosshairPoint,
    resolveHoveredFamily,
    resolveHoveredFamilyAfterDataRefresh,
    resolveNextHoveredFamily,
    type SeriesFamily,
} from '../atmDecayHover'

describe('atmDecayHover', () => {
    it('keeps baseline visibility in BOTH mode without hover', () => {
        const raw = buildSeriesVisualState({
            displayMode: 'both',
            hoveredFamily: null,
            family: 'put',
            layer: 'raw',
            baseColor: '#10b981',
        })
        const smooth = buildSeriesVisualState({
            displayMode: 'both',
            hoveredFamily: null,
            family: 'put',
            layer: 'smooth',
            baseColor: '#10b981',
        })

        expect(raw.visible).toBe(true)
        expect(raw.lineWidth).toBe(1)
        expect(raw.color).toContain('rgba(')
        expect(smooth.visible).toBe(true)
        expect(smooth.lineWidth).toBe(2)
        expect(smooth.color).toBe('#10b981')
    })

    it('de-emphasizes non-focused families while keeping focused family highlighted', () => {
        const focused = buildSeriesVisualState({
            displayMode: 'both',
            hoveredFamily: 'put',
            family: 'put',
            layer: 'smooth',
            baseColor: '#10b981',
        })
        const deEmphasized = buildSeriesVisualState({
            displayMode: 'both',
            hoveredFamily: 'put',
            family: 'call',
            layer: 'smooth',
            baseColor: '#ef4444',
        })

        expect(focused.lineWidth).toBe(2)
        expect(focused.crosshairMarkerVisible).toBe(true)
        expect(focused.lastValueVisible).toBe(true)

        expect(deEmphasized.visible).toBe(false)
        expect(deEmphasized.crosshairMarkerVisible).toBe(false)
        expect(deEmphasized.lastValueVisible).toBe(false)
        expect(deEmphasized.priceLineVisible).toBe(false)
    })

    it('keeps hover semantics symmetric across put/call/straddle in BOTH mode', () => {
        const families: SeriesFamily[] = ['put', 'call', 'straddle']
        for (const hoveredFamily of families) {
            for (const family of families) {
                const raw = buildSeriesVisualState({
                    displayMode: 'both',
                    hoveredFamily,
                    family,
                    layer: 'raw',
                    baseColor: '#10b981',
                })
                const smooth = buildSeriesVisualState({
                    displayMode: 'both',
                    hoveredFamily,
                    family,
                    layer: 'smooth',
                    baseColor: '#10b981',
                })
                const isFocus = family === hoveredFamily

                expect(raw.visible).toBe(isFocus)
                expect(smooth.visible).toBe(isFocus)
                expect(raw.lineWidth).toBe(1)
                expect(smooth.lineWidth).toBe(2)
            }
        }
    })

    it('keeps raw layer hidden in smoothed mode even with hover', () => {
        const raw = buildSeriesVisualState({
            displayMode: 'smoothed',
            hoveredFamily: 'straddle',
            family: 'straddle',
            layer: 'raw',
            baseColor: '#f59e0b',
        })
        const smooth = buildSeriesVisualState({
            displayMode: 'smoothed',
            hoveredFamily: 'straddle',
            family: 'straddle',
            layer: 'smooth',
            baseColor: '#f59e0b',
        })

        expect(raw.visible).toBe(false)
        expect(smooth.visible).toBe(true)
        expect(smooth.lineWidth).toBe(2)
    })

    it('resolves hovered family only when point and hoveredSeries are both present', () => {
        const targetSeries = { id: 'put-smooth' }
        const lookup = new Map<unknown, SeriesFamily>([[targetSeries, 'put']])
        const mkEvent = (event: Partial<MouseEventParams<Time>>): MouseEventParams<Time> => ({
            seriesData: new Map(),
            ...event,
        })

        expect(resolveHoveredFamily({
            event: mkEvent({ point: { x: 10 as never, y: 20 as never }, hoveredSeries: targetSeries as never }),
            seriesFamilyByApi: lookup,
        })).toBe('put')

        expect(resolveHoveredFamily({
            event: mkEvent({ point: undefined, hoveredSeries: targetSeries as never }),
            seriesFamilyByApi: lookup,
        })).toBeNull()

        expect(resolveHoveredFamily({
            event: mkEvent({ point: { x: 10 as never, y: 20 as never }, hoveredSeries: undefined }),
            seriesFamilyByApi: lookup,
        })).toBeNull()

        expect(resolveHoveredFamily({
            event: mkEvent({ point: { x: Number.NaN as never, y: 20 as never }, hoveredSeries: targetSeries as never }),
            seriesFamilyByApi: lookup,
        })).toBeNull()
    })

    it('requires strict TradingView hoveredSeries hit and clears focus when hit is absent', () => {
        const targetSeries = { id: 'put-smooth' }
        const lookup = new Map<unknown, SeriesFamily>([[targetSeries, 'put']])
        const mkEvent = (event: Partial<MouseEventParams<Time>>): MouseEventParams<Time> => ({
            seriesData: new Map(),
            ...event,
        })

        expect(resolveNextHoveredFamily({
            event: mkEvent({ point: { x: 10 as never, y: 20 as never }, hoveredSeries: targetSeries as never }),
            seriesFamilyByApi: lookup,
        })).toBe('put')

        expect(resolveNextHoveredFamily({
            event: mkEvent({ point: { x: 10 as never, y: 20 as never }, hoveredSeries: undefined }),
            currentHoveredFamily: 'put',
            seriesFamilyByApi: lookup,
        })).toBeNull()

        expect(resolveNextHoveredFamily({
            event: mkEvent({ point: undefined, hoveredSeries: undefined }),
            currentHoveredFamily: 'put',
            seriesFamilyByApi: lookup,
        })).toBeNull()

        expect(resolveNextHoveredFamily({
            event: mkEvent({ point: { x: Number.NaN as never, y: 20 as never }, hoveredSeries: undefined }),
            currentHoveredFamily: 'put',
            seriesFamilyByApi: lookup,
        })).toBeNull()
    })

    it('treats invalid crosshair coordinates as non-hover state', () => {
        expect(hasValidCrosshairPoint(undefined)).toBe(false)
        expect(hasValidCrosshairPoint({ x: Number.NaN as never, y: 20 as never })).toBe(false)
        expect(hasValidCrosshairPoint({ x: 20 as never, y: Number.POSITIVE_INFINITY as never })).toBe(false)
        expect(hasValidCrosshairPoint({ x: 20 as never, y: 20 as never })).toBe(true)
    })

    it('clears hovered family when no renderable data remains', () => {
        expect(resolveHoveredFamilyAfterDataRefresh({
            hasRenderableData: false,
            currentHoveredFamily: 'call',
        })).toBeNull()

        expect(resolveHoveredFamilyAfterDataRefresh({
            hasRenderableData: true,
            currentHoveredFamily: 'call',
        })).toBe('call')
    })
})

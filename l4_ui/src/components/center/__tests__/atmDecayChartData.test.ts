import { describe, expect, it } from 'vitest'
import { createEmptyChartStreamState, syncChartStreamState } from '../atmDecayChartData'

const BASE_ROWS = [
    {
        strike: 709,
        locked_at: '2026-04-21T13:29:59.000Z',
        timestamp: '2026-04-21T13:30:00.000Z',
        straddle_pct: 0.01,
        call_pct: 0.02,
        put_pct: -0.01,
        strike_changed: false,
    },
    {
        strike: 710,
        locked_at: '2026-04-21T13:30:01.000Z',
        timestamp: '2026-04-21T13:30:01.000Z',
        straddle_pct: 0.015,
        call_pct: 0.03,
        put_pct: -0.02,
        strike_changed: true,
    },
] as const

describe('atmDecayChartData', () => {
    it('builds an initial renderable stream state from market-hours rows', () => {
        const state = syncChartStreamState(createEmptyChartStreamState(), [...BASE_ROWS])

        expect(state.hasRenderableData).toBe(true)
        expect(state.rawSeriesPoints[0]).toHaveLength(2)
        expect(state.smoothSeriesPoints[1]).toHaveLength(2)
        expect(state.markers.some((marker) => marker.text === 'Strike Switch')).toBe(true)
        expect(state.lastDataLength).toBe(2)
    })

    it('incrementally appends tail rows without resetting prior points', () => {
        const initial = syncChartStreamState(createEmptyChartStreamState(), [...BASE_ROWS])
        const appended = syncChartStreamState(initial, [
            ...BASE_ROWS,
            {
                strike: 710,
                locked_at: '2026-04-21T13:30:02.000Z',
                timestamp: '2026-04-21T13:30:02.000Z',
                straddle_pct: 0.02,
                call_pct: 0.035,
                put_pct: -0.025,
                strike_changed: false,
            },
        ])

        expect(appended.rawSeriesPoints[0]).toHaveLength(3)
        expect(appended.rawSeriesPoints[0][0]).toEqual(initial.rawSeriesPoints[0][0])
        expect(appended.rawSeriesPoints[0][1]).toEqual(initial.rawSeriesPoints[0][1])
        expect(appended.markers).toHaveLength(initial.markers.length)
        expect(appended.lastDataLength).toBe(3)
    })

    it('returns the previous state when neither length nor tail signature changed', () => {
        const initial = syncChartStreamState(createEmptyChartStreamState(), [...BASE_ROWS])
        const unchanged = syncChartStreamState(initial, [...BASE_ROWS])

        expect(unchanged).toBe(initial)
    })
})

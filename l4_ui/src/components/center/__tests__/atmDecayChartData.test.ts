import { describe, expect, it } from 'vitest'
import { createEmptyChartStreamState, syncChartStreamState } from '../atmDecayChartData'

const BASE_ROWS = [
    {
        strike: 709,
        base_strike: 709,
        locked_at: '2026-04-21T13:29:59.000Z',
        timestamp: '2026-04-21T13:30:00.000Z',
        straddle_pct: 0.01,
        call_pct: 0.02,
        put_pct: -0.01,
        strike_changed: false,
    },
    {
        strike: 710,
        base_strike: 709,
        locked_at: '2026-04-21T13:29:59.000Z',
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
                base_strike: 709,
                locked_at: '2026-04-21T13:29:59.000Z',
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

    it('keeps full-day history and breaks the line across anchor changes', () => {
        const rows = [
            {
                strike: 753,
                base_strike: 753,
                locked_at: '09:30:08',
                timestamp: '2026-07-13T09:30:09.000-04:00',
                straddle_pct: 0.37,
                call_pct: -0.95,
                put_pct: 2.3,
                strike_changed: false,
            },
            {
                strike: 748,
                base_strike: 748,
                locked_at: '12:31:46',
                timestamp: '2026-07-13T12:31:47.000-04:00',
                straddle_pct: 0,
                call_pct: 0,
                put_pct: -0.01,
                strike_changed: false,
            },
            {
                strike: 748,
                base_strike: 748,
                locked_at: '12:31:46',
                timestamp: '2026-07-13T12:31:48.000-04:00',
                straddle_pct: 0.01,
                call_pct: -0.02,
                put_pct: 0.03,
                strike_changed: false,
            },
        ]

        const state = syncChartStreamState(createEmptyChartStreamState(), rows)

        expect(state.rawSeriesPoints[2].map((point) =>
            typeof point.value === 'number' ? Math.round(point.value) : null
        )).toEqual([230, null, -1, 3])
        expect(state.rawSeriesPoints[2].map((point) => point.time)).toEqual([1783949409, 1783960306, 1783960307, 1783960308])
        expect(state.lastDataLength).toBe(3)
    })

    it('breaks the line before stale recovery points', () => {
        const rows = [
            {
                strike: 753,
                base_strike: 753,
                locked_at: '09:30:08',
                timestamp: '2026-07-15T09:30:09.000-04:00',
                straddle_pct: 0.01,
                call_pct: 0.02,
                put_pct: -0.01,
                stale_recovery: false,
            },
            {
                strike: 753,
                base_strike: 753,
                locked_at: '09:30:08',
                timestamp: '2026-07-15T09:31:00.000-04:00',
                straddle_pct: 0.02,
                call_pct: 0.03,
                put_pct: -0.02,
                stale_recovery: true,
            },
        ]

        const state = syncChartStreamState(createEmptyChartStreamState(), rows)

        expect(state.rawSeriesPoints[1].map((point) =>
            typeof point.value === 'number' ? Math.round(point.value) : null
        )).toEqual([2, null, 3])
    })

    it('breaks the line when adjacent renderable timestamps gap by more than 30 seconds', () => {
        const rows = [
            {
                strike: 753,
                base_strike: 753,
                locked_at: '09:30:08',
                timestamp: '2026-07-15T09:30:09.000-04:00',
                straddle_pct: 0.01,
                call_pct: 0.02,
                put_pct: -0.01,
            },
            {
                strike: 753,
                base_strike: 753,
                locked_at: '09:30:08',
                timestamp: '2026-07-15T09:30:40.000-04:00',
                straddle_pct: 0.02,
                call_pct: 0.03,
                put_pct: -0.02,
            },
        ]

        const state = syncChartStreamState(createEmptyChartStreamState(), rows)

        expect(state.rawSeriesPoints[2].map((point) =>
            typeof point.value === 'number' ? Math.round(point.value) : null
        )).toEqual([-1, null, -2])
    })

    it('returns the previous state when neither length nor tail signature changed', () => {
        const initial = syncChartStreamState(createEmptyChartStreamState(), [...BASE_ROWS])
        const unchanged = syncChartStreamState(initial, [...BASE_ROWS])

        expect(unchanged).toBe(initial)
    })
})

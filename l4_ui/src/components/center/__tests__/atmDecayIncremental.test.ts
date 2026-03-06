import { describe, expect, it, vi } from 'vitest'
import type { Time } from 'lightweight-charts'
import {
    buildAtmSeriesSyncPlan,
    syncAtmSeriesData,
    type AtmSeriesApiLike,
    type AtmSeriesPoint,
} from '../atmDecayIncremental'

function p(time: number, value: number): AtmSeriesPoint {
    return { time: time as Time, value }
}

function makeSeriesMock(): AtmSeriesApiLike & {
    setData: ReturnType<typeof vi.fn>
    update: ReturnType<typeof vi.fn>
} {
    return {
        setData: vi.fn(),
        update: vi.fn(),
    }
}

describe('atmDecayIncremental', () => {
    it('uses update path for append-only ticks', () => {
        const prev = [p(1, 10), p(2, 20)]
        const next = [p(1, 10), p(2, 20), p(3, 30)]
        const series = makeSeriesMock()

        const plan = syncAtmSeriesData(series, prev, next)

        expect(plan.mode).toBe('update')
        expect(series.setData).not.toHaveBeenCalled()
        expect(series.update).toHaveBeenCalledTimes(2)
        expect(series.update).toHaveBeenNthCalledWith(1, p(2, 20))
        expect(series.update).toHaveBeenNthCalledWith(2, p(3, 30))
    })

    it('uses update path for same-timestamp overwrite', () => {
        const prev = [p(1, 10), p(2, 20)]
        const next = [p(1, 10), p(2, 25)]
        const series = makeSeriesMock()

        const plan = syncAtmSeriesData(series, prev, next)

        expect(plan.mode).toBe('update')
        expect(series.setData).not.toHaveBeenCalled()
        expect(series.update).toHaveBeenCalledTimes(1)
        expect(series.update).toHaveBeenCalledWith(p(2, 25))
    })

    it('falls back to setData for non-prefix reorder/backfill', () => {
        const prev = [p(2, 20), p(3, 30)]
        const next = [p(1, 10), p(2, 20), p(3, 30)]
        const series = makeSeriesMock()

        const plan = syncAtmSeriesData(series, prev, next)

        expect(plan.mode).toBe('setData')
        expect(series.setData).toHaveBeenCalledTimes(1)
        expect(series.setData).toHaveBeenCalledWith(next)
        expect(series.update).not.toHaveBeenCalled()
    })

    it('returns noop when series is unchanged', () => {
        const prev = [p(1, 10), p(2, 20)]
        const next = [p(1, 10), p(2, 20)]
        const plan = buildAtmSeriesSyncPlan(prev, next)

        expect(plan.mode).toBe('noop')
    })
})

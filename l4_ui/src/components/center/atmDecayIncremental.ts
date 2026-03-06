import type { Time } from 'lightweight-charts'

export type AtmSeriesPoint = { time: Time; value: number }

export interface AtmSeriesApiLike {
    setData: (data: AtmSeriesPoint[]) => void
    update: (point: AtmSeriesPoint) => void
}

export interface AtmSeriesSyncPlan {
    mode: 'setData' | 'update' | 'noop'
    startIndex: number
}

function isStrictlyAscending(points: AtmSeriesPoint[]): boolean {
    for (let i = 1; i < points.length; i += 1) {
        if ((points[i].time as number) <= (points[i - 1].time as number)) {
            return false
        }
    }
    return true
}

function hasTimePrefix(prev: AtmSeriesPoint[], next: AtmSeriesPoint[]): boolean {
    if (prev.length > next.length) {
        return false
    }
    for (let i = 0; i < prev.length; i += 1) {
        if ((prev[i].time as number) !== (next[i].time as number)) {
            return false
        }
    }
    return true
}

export function buildAtmSeriesSyncPlan(
    prev: AtmSeriesPoint[],
    next: AtmSeriesPoint[],
): AtmSeriesSyncPlan {
    if (next.length === 0 || prev.length === 0) {
        return { mode: 'setData', startIndex: 0 }
    }
    if (!isStrictlyAscending(next) || !hasTimePrefix(prev, next)) {
        return { mode: 'setData', startIndex: 0 }
    }
    if (next.length === prev.length) {
        const lastIdx = next.length - 1
        if (lastIdx < 0) {
            return { mode: 'noop', startIndex: 0 }
        }
        if (next[lastIdx].value === prev[lastIdx].value) {
            return { mode: 'noop', startIndex: next.length }
        }
        return { mode: 'update', startIndex: lastIdx }
    }
    return { mode: 'update', startIndex: Math.max(prev.length - 1, 0) }
}

export function syncAtmSeriesData(
    series: AtmSeriesApiLike,
    prev: AtmSeriesPoint[],
    next: AtmSeriesPoint[],
): AtmSeriesSyncPlan {
    const plan = buildAtmSeriesSyncPlan(prev, next)
    if (plan.mode === 'setData') {
        series.setData(next)
        return plan
    }
    if (plan.mode === 'update') {
        for (let i = plan.startIndex; i < next.length; i += 1) {
            series.update(next[i])
        }
    }
    return plan
}

import type { SeriesMarker, Time } from 'lightweight-charts'
import type { AtmDecay } from '../../types/dashboard'
import { THEME } from '../../lib/theme'
import { getHHMM, isMarketHours, toUnixSec } from './atmDecayTime'
import type { AtmSeriesPoint } from './atmDecayIncremental'
import type { DisplayMode, SeriesFamily } from './atmDecayHover'

export type ExtendedAtmDecay = AtmDecay & { strike_changed?: boolean }
export type AtmSeriesField = 'straddle_pct' | 'call_pct' | 'put_pct'

export const STORAGE_KEY = 'l4.atm_decay_display_mode'
export const SMOOTHING_ALPHA = 0.24
export const MODE_ITEMS: { key: DisplayMode; label: string }[] = [
    { key: 'smoothed', label: 'SMTH' },
    { key: 'raw', label: 'RAW' },
    { key: 'both', label: 'BOTH' },
]

export const SERIES_CFG: readonly { key: AtmSeriesField; label: string; color: string }[] = [
    { key: 'straddle_pct', label: 'STRADDLE', color: THEME.accent.amber },
    { key: 'call_pct', label: 'CALL', color: THEME.market.up },
    { key: 'put_pct', label: 'PUT', color: THEME.market.down },
] as const

export const SERIES_FAMILIES: readonly SeriesFamily[] = ['straddle', 'call', 'put'] as const

export interface AtmChartStreamState {
    rawSeriesPoints: AtmSeriesPoint[][]
    smoothSeriesPoints: AtmSeriesPoint[][]
    markers: SeriesMarker<Time>[]
    lastDataLength: number
    lastTimestamp: string | null
    lastTailSignature: string | null
    hasRenderableData: boolean
}

function emptySeriesPoints(): AtmSeriesPoint[][] {
    return SERIES_CFG.map(() => [])
}

function toSeriesValue(row: ExtendedAtmDecay, key: AtmSeriesField): number | null {
    const raw = row[key]
    return typeof raw === 'number' && Number.isFinite(raw) ? raw * 100 : null
}

function appendPoint(points: AtmSeriesPoint[], time: Time, value: number): void {
    const last = points[points.length - 1]
    if (!last || (last.time as number) < (time as number)) {
        points.push({ time, value })
        return
    }
    if ((last.time as number) === (time as number)) {
        last.value = value
    }
}

function appendSmoothedPoint(points: AtmSeriesPoint[], time: Time, value: number): void {
    const last = points[points.length - 1]
    if (!last || (last.time as number) < (time as number)) {
        const prevValue = last?.value ?? value
        const nextValue = points.length === 0 ? value : (SMOOTHING_ALPHA * value) + ((1 - SMOOTHING_ALPHA) * prevValue)
        points.push({ time, value: nextValue })
        return
    }
    if ((last.time as number) === (time as number)) {
        const prevValue = points.length > 1 ? points[points.length - 2].value : value
        last.value = points.length === 1 ? value : (SMOOTHING_ALPHA * value) + ((1 - SMOOTHING_ALPHA) * prevValue)
    }
}

function buildMarkerTail(rows: ExtendedAtmDecay[], cliffAlreadyAdded: boolean): {
    markers: SeriesMarker<Time>[]
    cliffAdded: boolean
} {
    const markers: SeriesMarker<Time>[] = []
    let cliffAdded = cliffAlreadyAdded

    for (const row of rows) {
        if (!row.timestamp || !isMarketHours(row.timestamp)) continue
        const unixTs = toUnixSec(row.timestamp)
        if (unixTs === null) continue
        const time = unixTs as Time
        const hhmm = getHHMM(row.timestamp)

        if (row.strike_changed) {
            markers.push({
                time,
                position: 'aboveBar',
                color: THEME.accent.amber,
                shape: 'arrowDown',
                text: 'Strike Switch',
            })
        }

        if (!cliffAdded && hhmm !== null && hhmm >= 1530 && hhmm < 1600) {
            markers.push({
                time,
                position: 'aboveBar',
                color: THEME.market.up,
                shape: 'arrowDown',
                text: '15:30 CLIFF',
            })
            cliffAdded = true
        }
    }

    return { markers, cliffAdded }
}

function buildTailSignature(row: ExtendedAtmDecay | undefined): string | null {
    if (!row?.timestamp) return null
    return [
        row.timestamp,
        row.straddle_pct ?? 'NA',
        row.call_pct ?? 'NA',
        row.put_pct ?? 'NA',
        row.strike_changed ? '1' : '0',
    ].join('|')
}

function pruneSeriesFromTime(points: AtmSeriesPoint[], fromTime: Time): AtmSeriesPoint[] {
    return points.filter((point) => (point.time as number) < (fromTime as number))
}

function pruneMarkersFromTime(markers: SeriesMarker<Time>[], fromTime: Time): SeriesMarker<Time>[] {
    return markers.filter((marker) => (marker.time as number) < (fromTime as number))
}

function canIncrementallyAppend(
    prev: AtmChartStreamState,
    rows: ExtendedAtmDecay[],
): boolean {
    if (prev.lastDataLength === 0 || rows.length === 0) return false
    if (rows.length < prev.lastDataLength) return false
    const overlap = rows[prev.lastDataLength - 1]
    if (!overlap?.timestamp || overlap.timestamp !== prev.lastTimestamp) return false
    return true
}

function buildTailFromRows(
    rows: ExtendedAtmDecay[],
    rawSeriesPoints: AtmSeriesPoint[][],
    smoothSeriesPoints: AtmSeriesPoint[][],
): boolean {
    let hasRenderableData = false

    for (const row of rows) {
        if (!row.timestamp || !isMarketHours(row.timestamp)) continue
        const unixTs = toUnixSec(row.timestamp)
        if (unixTs === null) continue
        const time = unixTs as Time

        SERIES_CFG.forEach(({ key }, index) => {
            const value = toSeriesValue(row, key)
            if (value === null) return
            appendPoint(rawSeriesPoints[index], time, value)
            appendSmoothedPoint(smoothSeriesPoints[index], time, value)
            hasRenderableData = true
        })
    }

    return hasRenderableData
}

export function createEmptyChartStreamState(): AtmChartStreamState {
    return {
        rawSeriesPoints: emptySeriesPoints(),
        smoothSeriesPoints: emptySeriesPoints(),
        markers: [],
        lastDataLength: 0,
        lastTimestamp: null,
        lastTailSignature: null,
        hasRenderableData: false,
    }
}

export function syncChartStreamState(
    prev: AtmChartStreamState,
    rows: ExtendedAtmDecay[],
): AtmChartStreamState {
    if (rows.length === 0) {
        return createEmptyChartStreamState()
    }

    const nextTailSignature = buildTailSignature(rows[rows.length - 1])
    if (
        rows.length === prev.lastDataLength
        && nextTailSignature !== null
        && nextTailSignature === prev.lastTailSignature
    ) {
        return prev
    }

    if (!canIncrementallyAppend(prev, rows)) {
        const next = createEmptyChartStreamState()
        next.hasRenderableData = buildTailFromRows(rows, next.rawSeriesPoints, next.smoothSeriesPoints)
        next.markers = buildMarkerTail(rows, false).markers
        next.lastDataLength = rows.length
        next.lastTimestamp = rows[rows.length - 1]?.timestamp ?? null
        next.lastTailSignature = nextTailSignature
        return next
    }

    const overlapRow = rows[Math.max(prev.lastDataLength - 1, 0)]
    if (!overlapRow?.timestamp || !isMarketHours(overlapRow.timestamp)) {
        return syncChartStreamState(createEmptyChartStreamState(), rows)
    }
    const overlapUnix = toUnixSec(overlapRow.timestamp)
    if (overlapUnix === null) {
        return syncChartStreamState(createEmptyChartStreamState(), rows)
    }
    const overlapTime = overlapUnix as Time

    const rawSeriesPoints = prev.rawSeriesPoints.map((points) => pruneSeriesFromTime(points, overlapTime))
    const smoothSeriesPoints = prev.smoothSeriesPoints.map((points) => pruneSeriesFromTime(points, overlapTime))
    const cliffAlreadyAdded = pruneMarkersFromTime(prev.markers, overlapTime).some((marker) => marker.text === '15:30 CLIFF')
    const markers = pruneMarkersFromTime(prev.markers, overlapTime)
    const tailRows = rows.slice(Math.max(prev.lastDataLength - 1, 0))
    const hasRenderableData = buildTailFromRows(tailRows, rawSeriesPoints, smoothSeriesPoints)
    const tailMarkers = buildMarkerTail(tailRows, cliffAlreadyAdded)

    return {
        rawSeriesPoints,
        smoothSeriesPoints,
        markers: [...markers, ...tailMarkers.markers],
        lastDataLength: rows.length,
        lastTimestamp: rows[rows.length - 1]?.timestamp ?? null,
        lastTailSignature: nextTailSignature,
        hasRenderableData,
    }
}

export function getInitialDisplayMode(): DisplayMode {
    if (typeof window === 'undefined') return 'smoothed'
    try {
        const value = window.localStorage.getItem(STORAGE_KEY)
        if (value === 'smoothed' || value === 'raw' || value === 'both') {
            return value
        }
    } catch {
        // no-op
    }
    return 'smoothed'
}

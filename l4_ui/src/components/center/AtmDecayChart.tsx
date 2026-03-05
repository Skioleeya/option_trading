/**
 * AtmDecayChart — TradingView Lightweight Charts v5.1
 *
 * Official API reference:
 *   https://tradingview.github.io/lightweight-charts/docs/api/interfaces/IChartApi#addseries
 *
 * Correct v5 pattern:
 *   import { createChart, LineSeries } from 'lightweight-charts'
 *   const series = chart.addSeries(LineSeries, { color: 'red' })
 */
import React, { useEffect, useRef, memo } from 'react'
import {
    createChart,
    ColorType,
    LineStyle,
    CrosshairMode,
    LineSeries,
    LineType,
    createSeriesMarkers,
    type IChartApi,
    type Time,
    type SeriesMarker,
    type ISeriesMarkersPluginApi,
} from 'lightweight-charts'
import { useDashboardStore, selectAtmHistory } from '../../store/dashboardStore'
import type { AtmDecay } from '../../types/dashboard'

// Extended AtmDecay to recognize the new L1 field gracefully
type ExtendedAtmDecay = AtmDecay & { strike_changed?: boolean }

interface Props {
    data?: AtmDecay[]
}

// ── Theme ──────────────────────────────────────────────────────────────────────
const BG = '#060606'
const GRID = 'rgba(255,255,255,0.04)'
const HAIR = '#52525b'
const TEXT = '#71717a'
const BORDER = '#27272a'

const SERIES_CFG = [
    { key: 'straddle_pct' as const, label: 'STRADDLE', color: '#f59e0b' },
    { key: 'call_pct' as const, label: 'CALL', color: '#ef4444' },
    { key: 'put_pct' as const, label: 'PUT', color: '#10b981' },
] as const

// ── Helpers ────────────────────────────────────────────────────────────────────
const toUnixSec = (ts: string) => Math.floor(new Date(ts).getTime() / 1000)


/**
 * Gate: keep only intraday ticks.
 * Optimized for performance: parse time directly from the ISO string
 * assuming backend emits NY local time or UTC string like "...T09:30...-05:00"
 */
function getHHMM(ts: string): number {
    const m = ts.match(/T(\d{2}):(\d{2})/)
    if (!m) return 0
    return parseInt(m[1], 10) * 100 + parseInt(m[2], 10)
}

function isMarketHours(ts: string): boolean {
    const t = getHHMM(ts)
    return t >= 925
}

function buildPoints(data: ExtendedAtmDecay[], key: keyof AtmDecay) {
    const seen = new Set<number>()
    return data
        .filter(d => d.timestamp && d[key] != null && isMarketHours(d.timestamp))
        .reduce<{ time: Time; value: number }[]>((acc, d) => {
            const t = toUnixSec(d.timestamp!)
            if (!seen.has(t)) { seen.add(t); acc.push({ time: t as Time, value: (d[key] as number) * 100 }) }
            return acc
        }, [])
        .sort((a, b) => (a.time as number) - (b.time as number))
}


// ── Component ─────────────────────────────────────────────────────────────────
export const AtmDecayChart: React.FC<Props> = memo(({ data: propData }) => {
    const storeData = useDashboardStore(selectAtmHistory) as ExtendedAtmDecay[]
    const data = storeData.length > 0 ? storeData : (propData as ExtendedAtmDecay[] ?? [])
    const containerRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<IChartApi | null>(null)
    // Using any for the series reference since the types for addSeries in v5 
    // vs the ISeriesApi interface have some strict generic variance
    const seriesRef = useRef<any[]>([])
    const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
    const markersRef = useRef<SeriesMarker<Time>[]>([])
    const initialised = useRef(false)
    const prevLen = useRef(0)
    const firstTimeRef = useRef<string | null>(null)
    const lastTimeRef = useRef<number>(0)
    const hasAddedCliff = useRef(false)

    // ── Chart init (mount only) ──────────────────────────────────────────────
    useEffect(() => {
        const el = containerRef.current
        if (!el) return

        const chart = createChart(el, {
            width: el.clientWidth || 600,
            height: el.clientHeight || 300,
            layout: {
                background: { type: ColorType.Solid, color: BG },
                textColor: TEXT,
                fontFamily: "'JetBrains Mono','Fira Mono',monospace",
                fontSize: 10,
            },
            grid: {
                vertLines: { color: GRID, style: LineStyle.SparseDotted },
                horzLines: { color: GRID, style: LineStyle.SparseDotted },
            },
            crosshair: {
                mode: CrosshairMode.Normal,
                vertLine: { color: HAIR, style: LineStyle.Solid, width: 1, labelBackgroundColor: '#18181b' },
                horzLine: { color: HAIR, style: LineStyle.Solid, width: 1, labelBackgroundColor: '#18181b' },
            },
            localization: {
                timeFormatter: (time: number) =>
                    new Date(time * 1000).toLocaleTimeString('en-US', {
                        timeZone: 'America/New_York',
                        hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
                    })
            },
            rightPriceScale: { borderColor: BORDER },
            timeScale: {
                borderColor: BORDER,
                timeVisible: true,
                secondsVisible: true,
                minBarSpacing: 0.001, // Enables infinite horizontal zoom-out limits
                tickMarkFormatter: (time: number) => {
                    return new Date(time * 1000).toLocaleTimeString('en-US', {
                        timeZone: 'America/New_York',
                        hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
                    })
                }
            },
        })

        // Official v5 API: chart.addSeries(LineSeries, options)
        // Returns ISeriesApi<"Line", Time, SeriesDataItemTypeMap<Time>["Line"], ...>
        const srs = SERIES_CFG.map(({ color }) =>
            chart.addSeries(LineSeries, {
                color,
                lineWidth: 1, // Adjusted to 1px width
                lineType: LineType.WithSteps,
                priceLineVisible: true,
                priceLineStyle: LineStyle.Dashed,
                priceLineWidth: 1,
                lastValueVisible: true,
                crosshairMarkerRadius: 3,
                crosshairMarkerBackgroundColor: color,
                priceFormat: {
                    type: 'custom',
                    formatter: (p: number) => `${p > 0 ? '+' : ''}${p.toFixed(1)}%`,
                    minMove: 0.1,
                },
            })
        )

        // Zero-axis reference price line
        srs[0]?.createPriceLine({
            price: 0,
            color: 'rgba(255,255,255,0.18)',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: false,
        })

        chartRef.current = chart
        seriesRef.current = srs

        // Initialize markers plugin on the primary series
        if (srs[0]) {
            markersPluginRef.current = createSeriesMarkers(srs[0])
        }

        // Responsive resize via ResizeObserver
        const ro = new ResizeObserver(entries => {
            const c = chartRef.current
            if (!c || !entries.length) return
            const { width, height } = entries[0].contentRect
            c.applyOptions({ width, height })
        })
        ro.observe(el)

        return () => {
            ro.disconnect()
            chart.remove()
            chartRef.current = null
            seriesRef.current = []
            markersPluginRef.current?.detach()
            markersPluginRef.current = null
            markersRef.current = []
            initialised.current = false
            prevLen.current = 0
            lastTimeRef.current = 0
        }
    }, [])

    // ── Data sync ─────────────────────────────────────────────────────────────
    useEffect(() => {
        const chart = chartRef.current
        const srs = seriesRef.current
        if (!chart || !srs.length || !data.length) return

        // OPTIMIZATION: Skip chart updates if tab is hidden
        if (document.visibilityState === 'hidden') {
            prevLen.current = data.length
            return
        }

        // Determine if we need a full reload vs incremental update.
        // Re-run full load if:
        // 1. Not initialized
        // 2. Data size jumped significantly (e.g. history arrived)
        // 3. The first data point changed (e.g. history prepended)
        const isJump = data.length > prevLen.current + 5
        const isFirstPointChanged = data[0]?.timestamp !== firstTimeRef.current

        if (!initialised.current || isJump || isFirstPointChanged) {
            let anyDataLoaded = false
            const nextMarkers: SeriesMarker<Time>[] = []

            // Reset state for full reload
            lastTimeRef.current = 0
            hasAddedCliff.current = false
            firstTimeRef.current = data[0]?.timestamp ?? null

            SERIES_CFG.forEach(({ key }, i) => {
                const pts = buildPoints(data, key)
                if (pts.length) {
                    const series = srs[i];
                    if (series && typeof series.setData === 'function') {
                        series.setData(pts)
                    } else {
                        console.warn(`[AtmDecayChart] series[${i}] has no setData method`, series);
                    }
                    const lastPt = pts[pts.length - 1]
                    if (lastPt) {
                        lastTimeRef.current = Math.max(lastTimeRef.current, lastPt.time as number)
                    }
                    anyDataLoaded = true
                }
            })

            data.forEach(d => {
                if (!d.timestamp || !isMarketHours(d.timestamp)) return

                const t = toUnixSec(d.timestamp) as Time
                const hhmm = getHHMM(d.timestamp)

                if (d.strike_changed) {
                    nextMarkers.push({
                        time: t,
                        position: 'aboveBar',
                        color: '#fbbf24',
                        shape: 'arrowDown',
                        text: `Strike Switch`,
                    })
                }

                if (!hasAddedCliff.current && hhmm >= 1530 && hhmm < 1600) {
                    nextMarkers.push({
                        time: t,
                        position: 'aboveBar',
                        color: '#ef4444',
                        shape: 'arrowDown',
                        text: `15:30 CLIFF`,
                    })
                    hasAddedCliff.current = true
                }
            })

            if (anyDataLoaded) {
                if (nextMarkers.length > 0) {
                    const plugin = markersPluginRef.current;
                    if (plugin && typeof plugin.setMarkers === 'function') {
                        plugin.setMarkers(nextMarkers)
                        markersRef.current = nextMarkers
                    } else {
                        console.error('[AtmDecayChart] setMarkers failed on mount: markers plugin missing', plugin);
                    }
                }
                chart.timeScale().fitContent()
                initialised.current = true
                prevLen.current = data.length
            }
            // If no data yet, leave initialised=false so we retry on next tick
        } else {
            // Incremental tick append
            const delta = data.length - prevLen.current
            if (delta <= 0) return
            const newTicks = data.slice(-delta)

            let updatedMarkers = false
            const nextMarkers = [...markersRef.current]

            newTicks.forEach(tick => {
                if (!tick.timestamp || !isMarketHours(tick.timestamp)) return
                const t = toUnixSec(tick.timestamp)
                if (t <= lastTimeRef.current) return // CHRONOLOGICAL GUARD

                SERIES_CFG.forEach(({ key }, i) => {
                    const v = tick[key]
                    if (v != null) {
                        const series = srs[i];
                        if (series && typeof series.update === 'function') {
                            series.update({ time: t as Time, value: (v as number) * 100 })
                        }
                    }
                })

                if (tick.strike_changed) {
                    nextMarkers.push({
                        time: t as Time,
                        position: 'aboveBar',
                        color: '#fbbf24',
                        shape: 'arrowDown',
                        text: `Strike Switch`,
                    })
                    updatedMarkers = true
                }

                const hhmm = getHHMM(tick.timestamp)
                if (!hasAddedCliff.current && hhmm >= 1530 && hhmm < 1600) {
                    nextMarkers.push({
                        time: t as Time,
                        position: 'aboveBar',
                        color: '#ef4444',
                        shape: 'arrowDown',
                        text: `15:30 CLIFF`,
                    })
                    hasAddedCliff.current = true
                    updatedMarkers = true
                }

                lastTimeRef.current = t
            })

            if (updatedMarkers) {
                const plugin = markersPluginRef.current;
                if (plugin && typeof plugin.setMarkers === 'function') {
                    plugin.setMarkers(nextMarkers)
                    markersRef.current = nextMarkers
                } else {
                    console.error('[AtmDecayChart] setMarkers failed on update: markers plugin missing', plugin);
                }
            }

            prevLen.current = data.length
        }
    }, [data])



    return (
        <div className="relative w-full h-full">
            <div ref={containerRef} className="w-full h-full" style={{ touchAction: 'none' }} />
        </div>
    )
})

AtmDecayChart.displayName = 'AtmDecayChart'
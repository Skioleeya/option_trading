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
import React, { useEffect, useRef, memo, useState, useCallback } from 'react'
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
    type MouseEventParams,
} from 'lightweight-charts'
import { useDashboardStore, selectAtmHistory } from '../../store/dashboardStore'
import type { AtmDecay } from '../../types/dashboard'
import { getHHMM, getMarketSessionWindowUnixSec, isMarketHours, toUnixSec } from './atmDecayTime'
import { syncAtmSeriesData, type AtmSeriesPoint } from './atmDecayIncremental'
import {
    buildSeriesVisualState,
    resolveHoveredFamilyAfterDataRefresh,
    resolveNextHoveredFamily,
    type DisplayMode,
    type SeriesFamily,
} from './atmDecayHover'

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
const STORAGE_KEY = 'l4.atm_decay_display_mode'
const SMOOTHING_ALPHA = 0.24
const MODE_ITEMS: { key: DisplayMode; label: string }[] = [
    { key: 'smoothed', label: 'SMTH' },
    { key: 'raw', label: 'RAW' },
    { key: 'both', label: 'BOTH' },
]

const SERIES_CFG = [
    { key: 'straddle_pct' as const, label: 'STRADDLE', color: '#f59e0b' },
    { key: 'call_pct' as const, label: 'CALL', color: '#ef4444' },
    { key: 'put_pct' as const, label: 'PUT', color: '#10b981' },
] as const

const SERIES_FAMILIES: SeriesFamily[] = ['straddle', 'call', 'put']

// ── Helpers ────────────────────────────────────────────────────────────────────

function buildPoints(data: ExtendedAtmDecay[], key: keyof AtmDecay) {
    const seen = new Set<number>()
    return data
        .filter(d => d.timestamp && d[key] != null && isMarketHours(d.timestamp))
        .reduce<{ time: Time; value: number }[]>((acc, d) => {
            const t = toUnixSec(d.timestamp!)
            if (t === null) return acc
            if (!seen.has(t)) { seen.add(t); acc.push({ time: t as Time, value: (d[key] as number) * 100 }) }
            return acc
        }, [])
        .sort((a, b) => (a.time as number) - (b.time as number))
}

function buildSmoothedPoints(points: { time: Time; value: number }[], alpha: number) {
    if (!points.length) return points
    let ewma = points[0].value
    return points.map((p, idx) => {
        if (idx === 0) return p
        ewma = alpha * p.value + (1 - alpha) * ewma
        return { time: p.time, value: ewma }
    })
}

function getInitialDisplayMode(): DisplayMode {
    if (typeof window === 'undefined') return 'smoothed'
    try {
        const v = window.localStorage.getItem(STORAGE_KEY)
        if (v === 'smoothed' || v === 'raw' || v === 'both') return v
    } catch {
        // no-op
    }
    return 'smoothed'
}

// ── Component ─────────────────────────────────────────────────────────────────
export const AtmDecayChart: React.FC<Props> = memo(({ data: propData }) => {
    const storeData = useDashboardStore(selectAtmHistory) as ExtendedAtmDecay[]
    const data = storeData.length > 0 ? storeData : (propData as ExtendedAtmDecay[] ?? [])
    const [displayMode, setDisplayMode] = useState<DisplayMode>(getInitialDisplayMode)
    const containerRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<IChartApi | null>(null)
    // Using any for series refs because v5 addSeries() generic variance is strict.
    const rawSeriesRef = useRef<any[]>([])
    const smoothSeriesRef = useRef<any[]>([])
    const rawSeriesPointsRef = useRef<AtmSeriesPoint[][]>([])
    const smoothSeriesPointsRef = useRef<AtmSeriesPoint[][]>([])
    const rawMarkersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
    const smoothMarkersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
    const markersRef = useRef<SeriesMarker<Time>[]>([])
    const seriesFamilyByApiRef = useRef<Map<unknown, SeriesFamily>>(new Map())
    const hoveredFamilyRef = useRef<SeriesFamily | null>(null)
    const displayModeRef = useRef<DisplayMode>(displayMode)
    const initialised = useRef(false)
    const hasAddedCliff = useRef(false)

    const applySeriesVisualState = useCallback(
        (mode: DisplayMode, hoveredFamily: SeriesFamily | null) => {
            const rawSeries = rawSeriesRef.current
            const smoothSeries = smoothSeriesRef.current
            if (!rawSeries.length || !smoothSeries.length) return

            SERIES_CFG.forEach(({ color }, i) => {
                const family = SERIES_FAMILIES[i]
                const raw = rawSeries[i]
                const smooth = smoothSeries[i]

                if (raw && typeof raw.applyOptions === 'function') {
                    raw.applyOptions(
                        buildSeriesVisualState({
                            displayMode: mode,
                            hoveredFamily,
                            family,
                            layer: 'raw',
                            baseColor: color,
                        })
                    )
                }

                if (smooth && typeof smooth.applyOptions === 'function') {
                    smooth.applyOptions(
                        buildSeriesVisualState({
                            displayMode: mode,
                            hoveredFamily,
                            family,
                            layer: 'smooth',
                            baseColor: color,
                        })
                    )
                }
            })
        },
        []
    )

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

        const rawSeries = SERIES_CFG.map(({ color }) =>
            chart.addSeries(LineSeries, {
                color,
                lineWidth: 1,
                lineType: LineType.Simple,
                priceLineVisible: false,
                lastValueVisible: false,
                crosshairMarkerVisible: false,
                priceFormat: {
                    type: 'custom',
                    formatter: (p: number) => `${p > 0 ? '+' : ''}${p.toFixed(1)}%`,
                    minMove: 0.1,
                },
            })
        )

        const smoothSeries = SERIES_CFG.map(({ color }) =>
            chart.addSeries(LineSeries, {
                color,
                lineWidth: 2,
                lineType: LineType.Simple,
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
        smoothSeries[0]?.createPriceLine({
            price: 0,
            color: 'rgba(255,255,255,0.18)',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: false,
        })

        chartRef.current = chart
        rawSeriesRef.current = rawSeries
        smoothSeriesRef.current = smoothSeries
        const byApi = new Map<unknown, SeriesFamily>()
        SERIES_FAMILIES.forEach((family, i) => {
            if (rawSeries[i]) byApi.set(rawSeries[i], family)
            if (smoothSeries[i]) byApi.set(smoothSeries[i], family)
        })
        seriesFamilyByApiRef.current = byApi

        if (rawSeries[0]) {
            rawMarkersPluginRef.current = createSeriesMarkers(rawSeries[0])
        }
        if (smoothSeries[0]) {
            smoothMarkersPluginRef.current = createSeriesMarkers(smoothSeries[0])
        }

        const handleCrosshairMove = (event: MouseEventParams<Time>) => {
            const nextFamily = resolveNextHoveredFamily({
                event,
                currentHoveredFamily: hoveredFamilyRef.current,
                seriesFamilyByApi: seriesFamilyByApiRef.current,
            })
            if (hoveredFamilyRef.current === nextFamily) return
            hoveredFamilyRef.current = nextFamily
            applySeriesVisualState(displayModeRef.current, nextFamily)
        }
        const handleMouseLeave = () => {
            if (hoveredFamilyRef.current === null) return
            hoveredFamilyRef.current = null
            applySeriesVisualState(displayModeRef.current, null)
        }
        chart.subscribeCrosshairMove(handleCrosshairMove)
        el.addEventListener('mouseleave', handleMouseLeave)
        applySeriesVisualState(displayModeRef.current, hoveredFamilyRef.current)

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
            rawSeriesRef.current = []
            smoothSeriesRef.current = []
            rawSeriesPointsRef.current = []
            smoothSeriesPointsRef.current = []
            rawMarkersPluginRef.current?.detach()
            smoothMarkersPluginRef.current?.detach()
            chart.unsubscribeCrosshairMove(handleCrosshairMove)
            el.removeEventListener('mouseleave', handleMouseLeave)
            rawMarkersPluginRef.current = null
            smoothMarkersPluginRef.current = null
            markersRef.current = []
            seriesFamilyByApiRef.current = new Map()
            hoveredFamilyRef.current = null
            initialised.current = false
        }
    }, [applySeriesVisualState])

    // Persist display mode preference
    useEffect(() => {
        try {
            window.localStorage.setItem(STORAGE_KEY, displayMode)
        } catch {
            // no-op
        }
    }, [displayMode])

    // Display mode controls visibility and styling only (data remains raw in store/backend)
    useEffect(() => {
        displayModeRef.current = displayMode
        applySeriesVisualState(displayMode, hoveredFamilyRef.current)
    }, [displayMode, applySeriesVisualState])

    // ── Data sync ─────────────────────────────────────────────────────────────
    useEffect(() => {
        const chart = chartRef.current
        const rawSeries = rawSeriesRef.current
        const smoothSeries = smoothSeriesRef.current
        if (!chart || !rawSeries.length || !smoothSeries.length) return

        // OPTIMIZATION: Skip chart updates if tab is hidden
        if (document.visibilityState === 'hidden') {
            return
        }

        if (!data.length) {
            rawSeries.forEach((s) => {
                if (s && typeof s.setData === 'function') s.setData([])
            })
            smoothSeries.forEach((s) => {
                if (s && typeof s.setData === 'function') s.setData([])
            })
            rawSeriesPointsRef.current = []
            smoothSeriesPointsRef.current = []
            const rp = rawMarkersPluginRef.current
            const sp = smoothMarkersPluginRef.current
            if (rp && typeof rp.setMarkers === 'function') rp.setMarkers([])
            if (sp && typeof sp.setMarkers === 'function') sp.setMarkers([])
            markersRef.current = []
            initialised.current = false
            const nextHoveredFamily = resolveHoveredFamilyAfterDataRefresh({
                hasRenderableData: false,
                currentHoveredFamily: hoveredFamilyRef.current,
            })
            if (nextHoveredFamily !== hoveredFamilyRef.current) {
                hoveredFamilyRef.current = nextHoveredFamily
                applySeriesVisualState(displayModeRef.current, nextHoveredFamily)
            }
            return
        }

        let anyDataLoaded = false
        SERIES_CFG.forEach(({ key }, i) => {
            const rawPts = buildPoints(data, key)
            const smoothPts = buildSmoothedPoints(rawPts, SMOOTHING_ALPHA)
            const raw = rawSeries[i]
            const smooth = smoothSeries[i]

            if (raw && typeof raw.setData === 'function' && typeof raw.update === 'function') {
                syncAtmSeriesData(
                    raw,
                    rawSeriesPointsRef.current[i] ?? [],
                    rawPts,
                )
            }
            if (smooth && typeof smooth.setData === 'function' && typeof smooth.update === 'function') {
                syncAtmSeriesData(
                    smooth,
                    smoothSeriesPointsRef.current[i] ?? [],
                    smoothPts,
                )
            }
            rawSeriesPointsRef.current[i] = rawPts
            smoothSeriesPointsRef.current[i] = smoothPts
            if (rawPts.length) {
                anyDataLoaded = true
            }
        })

        const nextMarkers: SeriesMarker<Time>[] = []
        hasAddedCliff.current = false
        data.forEach(d => {
            if (!d.timestamp || !isMarketHours(d.timestamp)) return
            const ts = toUnixSec(d.timestamp)
            if (ts === null) return
            const t = ts as Time
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

            if (!hasAddedCliff.current && hhmm !== null && hhmm >= 1530 && hhmm < 1600) {
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

        const rp = rawMarkersPluginRef.current
        const sp = smoothMarkersPluginRef.current
        if (rp && typeof rp.setMarkers === 'function') rp.setMarkers(nextMarkers)
        if (sp && typeof sp.setMarkers === 'function') sp.setMarkers(nextMarkers)
        markersRef.current = nextMarkers

        if (!anyDataLoaded) {
            initialised.current = false
            const nextHoveredFamily = resolveHoveredFamilyAfterDataRefresh({
                hasRenderableData: false,
                currentHoveredFamily: hoveredFamilyRef.current,
            })
            if (nextHoveredFamily !== hoveredFamilyRef.current) {
                hoveredFamilyRef.current = nextHoveredFamily
                applySeriesVisualState(displayModeRef.current, nextHoveredFamily)
            }
            return
        }

        if (!initialised.current) {
            const lastMarketTick = [...data]
                .reverse()
                .find((d) => d.timestamp && isMarketHours(d.timestamp))
            const sessionWindow = lastMarketTick?.timestamp
                ? getMarketSessionWindowUnixSec(lastMarketTick.timestamp)
                : null

            if (sessionWindow) {
                chart.timeScale().setVisibleRange({
                    from: sessionWindow.from as Time,
                    to: sessionWindow.to as Time,
                })
            } else {
                chart.timeScale().fitContent()
            }
            initialised.current = true
        }
    }, [data])



    return (
        <div className="relative w-full h-full">
            <div ref={containerRef} className="w-full h-full" style={{ touchAction: 'none' }} />
            <div className="absolute top-4 right-4 z-20 pointer-events-auto">
                <div className="inline-flex items-center rounded-md border border-[#27272a] bg-[#0b0c0f]/90 p-0.5">
                    {MODE_ITEMS.map((m) => {
                        const active = displayMode === m.key
                        return (
                            <button
                                key={m.key}
                                type="button"
                                onClick={() => setDisplayMode(m.key)}
                                className={`px-2 py-1 text-[10px] font-bold tracking-wider transition-colors ${active
                                    ? 'bg-[#18181b] text-[#e4e4e7]'
                                    : 'text-[#71717a] hover:text-[#d4d4d8]'
                                    }`}
                            >
                                {m.label}
                            </button>
                        )
                    })}
                </div>
            </div>
        </div>
    )
})

AtmDecayChart.displayName = 'AtmDecayChart'

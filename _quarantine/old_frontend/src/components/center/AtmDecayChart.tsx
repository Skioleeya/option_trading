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
import React, { useEffect, useRef } from 'react'
import {
    createChart,
    ColorType,
    LineStyle,
    CrosshairMode,
    LineSeries,
    LineType,
    type IChartApi,
    type ISeriesApi,
    type SeriesOptionsMap,
    type Time,
} from 'lightweight-charts'
import type { AtmDecay } from '../../types/dashboard'

interface Props {
    data: AtmDecay[]
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

const formatET = (time: number) =>
    new Date(time * 1000).toLocaleTimeString('en-US', {
        timeZone: 'America/New_York',
        hour12: false, hour: '2-digit', minute: '2-digit',
    })

function isMarketHours(ts: string): boolean {
    const s = new Date(ts).toLocaleTimeString('en-US', {
        timeZone: 'America/New_York', hour: 'numeric', minute: 'numeric', hour12: false,
    })
    const [h, m] = s.split(':').map(Number)
    const t = h * 100 + m
    return t >= 925 && t <= 1615
}

function buildPoints(data: AtmDecay[], key: keyof AtmDecay) {
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
// The return type of chart.addSeries(LineSeries, ...) per the official v5 docs is
// ISeriesApi<"Line", ...>  where "Line" is a key of SeriesOptionsMap.
type LineSeries = ISeriesApi<keyof SeriesOptionsMap>

export const AtmDecayChart: React.FC<Props> = ({ data }) => {
    const containerRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<IChartApi | null>(null)
    const seriesRef = useRef<LineSeries[]>([])
    const initialised = useRef(false)
    const prevLen = useRef(0)
    const lastTimeRef = useRef<number>(0)

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
            localization: { timeFormatter: formatET },
            rightPriceScale: { borderColor: BORDER },
            timeScale: { borderColor: BORDER, timeVisible: true, secondsVisible: true },
        })

        // Official v5 API: chart.addSeries(LineSeries, options)
        // Returns ISeriesApi<"Line", Time, SeriesDataItemTypeMap<Time>["Line"], ...>
        const srs = SERIES_CFG.map(({ color }) =>
            chart.addSeries(LineSeries, {
                color,
                lineWidth: 2,
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

        if (!initialised.current) {
            // Full initial load
            SERIES_CFG.forEach(({ key }, i) => {
                const pts = buildPoints(data, key)
                if (pts.length) {
                    srs[i]?.setData(pts)
                    const lastPt = pts[pts.length - 1]
                    if (lastPt) {
                        lastTimeRef.current = Math.max(lastTimeRef.current, lastPt.time as number)
                    }
                }
            })
            chart.timeScale().fitContent()
            initialised.current = true
            prevLen.current = data.length
        } else {
            // Incremental tick append
            const delta = data.length - prevLen.current
            if (delta <= 0) return
            const newTicks = data.slice(-delta)

            newTicks.forEach(tick => {
                if (!tick.timestamp || !isMarketHours(tick.timestamp)) return
                const t = toUnixSec(tick.timestamp)
                if (t <= lastTimeRef.current) return // CHRONOLOGICAL GUARD

                SERIES_CFG.forEach(({ key }, i) => {
                    const v = tick[key]
                    if (v != null) {
                        srs[i]?.update({ time: t as Time, value: (v as number) * 100 })
                    }
                })
                lastTimeRef.current = t
            })
            prevLen.current = data.length
        }
    }, [data])


    return (
        <div className="relative w-full h-full">
            <div ref={containerRef} className="w-full h-full" style={{ touchAction: 'none' }} />
        </div>
    )
}
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
    type ISeriesMarkersPluginApi,
} from 'lightweight-charts'
import type { ChartEngineKey } from '../../config/runtime'

interface SeriesConfig {
    color: string
}

export interface AtmChartRuntime {
    engine: ChartEngineKey
    chart: IChartApi
    rawSeries: any[]
    smoothSeries: any[]
    rawMarkersPlugin: ISeriesMarkersPluginApi<Time> | null
    smoothMarkersPlugin: ISeriesMarkersPluginApi<Time> | null
}

const BG = '#060606'
const GRID = 'rgba(255,255,255,0.04)'
const HAIR = '#52525b'
const TEXT = '#71717a'
const BORDER = '#27272a'

function createLightweightRuntime(container: HTMLElement, seriesCfg: readonly SeriesConfig[]): AtmChartRuntime {
    const chart = createChart(container, {
        width: container.clientWidth || 600,
        height: container.clientHeight || 300,
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
            tickMarkFormatter: (time: number) =>
                new Date(time * 1000).toLocaleTimeString('en-US', {
                    timeZone: 'America/New_York',
                    hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
                }),
        },
    })

    const rawSeries = seriesCfg.map(({ color }) =>
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

    const smoothSeries = seriesCfg.map(({ color }) =>
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

    return {
        engine: 'lightweight',
        chart,
        rawSeries,
        smoothSeries,
        rawMarkersPlugin: rawSeries[0] ? createSeriesMarkers(rawSeries[0]) : null,
        smoothMarkersPlugin: smoothSeries[0] ? createSeriesMarkers(smoothSeries[0]) : null,
    }
}

export function createAtmChartRuntime(
    container: HTMLElement,
    engine: ChartEngineKey,
    seriesCfg: readonly SeriesConfig[],
): AtmChartRuntime {
    // Phase A only enables lightweight engine in production path.
    if (engine !== 'lightweight') {
        console.warn('[L4 ChartEngine] Unsupported engine "%s", fallback to lightweight.', engine)
    }
    return createLightweightRuntime(container, seriesCfg)
}

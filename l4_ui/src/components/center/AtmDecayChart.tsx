/**
 * AtmDecayChart — TradingView Lightweight Charts v5.1
 *
 * Uses incremental series updates on the hot path. Full rebuild is reserved
 * for history resets or non-append data changes.
 */
import React, { memo, useCallback, useEffect, useRef, useState } from 'react'
import {
    type IChartApi,
    type ISeriesMarkersPluginApi,
    type MouseEventParams,
    type Time,
} from 'lightweight-charts'
import { runtimeConfig } from '../../config/runtime'
import { useDashboardStore, selectAtmHistory } from '../../store/dashboardStore'
import type { AtmDecay } from '../../types/dashboard'
import { getMarketSessionWindowUnixSec, isMarketHours } from './atmDecayTime'
import { syncAtmSeriesData } from './atmDecayIncremental'
import {
    buildSeriesVisualState,
    resolveHoveredFamilyAfterDataRefresh,
    resolveNextHoveredFamily,
    type DisplayMode,
    type SeriesFamily,
} from './atmDecayHover'
import { createAtmChartRuntime } from './chartEngineAdapter'
import {
    createEmptyChartStreamState,
    getInitialDisplayMode,
    MODE_ITEMS,
    SERIES_CFG,
    SERIES_FAMILIES,
    STORAGE_KEY,
    syncChartStreamState,
    type AtmChartStreamState,
    type ExtendedAtmDecay,
} from './atmDecayChartData'

interface Props {
    data?: AtmDecay[]
}

type ChartDegradeStage = 'init' | 'update' | 'interaction' | 'resize'

function findLastMarketTick(data: ExtendedAtmDecay[]): ExtendedAtmDecay | null {
    for (let index = data.length - 1; index >= 0; index -= 1) {
        const row = data[index]
        if (row.timestamp && isMarketHours(row.timestamp)) {
            return row
        }
    }
    return null
}

export const AtmDecayChart: React.FC<Props> = memo(({ data: propData }) => {
    const storeData = useDashboardStore(selectAtmHistory) as ExtendedAtmDecay[]
    const data = storeData.length > 0 ? storeData : (propData as ExtendedAtmDecay[] ?? [])
    const [displayMode, setDisplayMode] = useState<DisplayMode>(getInitialDisplayMode)
    const [degradedStage, setDegradedStage] = useState<ChartDegradeStage | null>(null)
    const containerRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<IChartApi | null>(null)
    const rawSeriesRef = useRef<any[]>([])
    const smoothSeriesRef = useRef<any[]>([])
    const rawMarkersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
    const smoothMarkersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
    const seriesFamilyByApiRef = useRef<Map<unknown, SeriesFamily>>(new Map())
    const hoveredFamilyRef = useRef<SeriesFamily | null>(null)
    const displayModeRef = useRef<DisplayMode>(displayMode)
    const degradedStageRef = useRef<ChartDegradeStage | null>(null)
    const initialisedRef = useRef(false)
    const streamStateRef = useRef<AtmChartStreamState>(createEmptyChartStreamState())

    const applySeriesVisualState = useCallback((mode: DisplayMode, hoveredFamily: SeriesFamily | null) => {
        const rawSeries = rawSeriesRef.current
        const smoothSeries = smoothSeriesRef.current
        if (!rawSeries.length || !smoothSeries.length) return

        SERIES_CFG.forEach(({ color }, index) => {
            const family = SERIES_FAMILIES[index]
            const raw = rawSeries[index]
            const smooth = smoothSeries[index]
            const shared = {
                displayMode: mode,
                hoveredFamily,
                family,
                baseColor: color,
            }
            raw?.applyOptions?.(buildSeriesVisualState({ ...shared, layer: 'raw' }))
            smooth?.applyOptions?.(buildSeriesVisualState({ ...shared, layer: 'smooth' }))
        })
    }, [])

    const teardownChartRuntime = useCallback(() => {
        try {
            rawMarkersPluginRef.current?.detach?.()
            smoothMarkersPluginRef.current?.detach?.()
            chartRef.current?.remove?.()
        } catch (error) {
            console.warn('[AtmDecayChart] Failed to teardown chart runtime.', error)
        }
        chartRef.current = null
        rawSeriesRef.current = []
        smoothSeriesRef.current = []
        rawMarkersPluginRef.current = null
        smoothMarkersPluginRef.current = null
        seriesFamilyByApiRef.current = new Map()
        hoveredFamilyRef.current = null
        initialisedRef.current = false
        streamStateRef.current = createEmptyChartStreamState()
    }, [])

    const enterDegradedMode = useCallback((stage: ChartDegradeStage, error: unknown) => {
        if (degradedStageRef.current !== null) return
        console.error('[AtmDecayChart] Entering degraded mode at stage=%s.', stage, error)
        teardownChartRuntime()
        degradedStageRef.current = stage
        setDegradedStage(stage)
    }, [teardownChartRuntime])

    const syncLatestChartState = useCallback((rows: ExtendedAtmDecay[]) => {
        if (degradedStageRef.current !== null) return

        const chart = chartRef.current
        const rawSeries = rawSeriesRef.current
        const smoothSeries = smoothSeriesRef.current
        if (!chart || !rawSeries.length || !smoothSeries.length) return

        try {
            const prevStreamState = streamStateRef.current
            const nextStreamState = syncChartStreamState(prevStreamState, rows)
            if (nextStreamState === prevStreamState) {
                return
            }
            streamStateRef.current = nextStreamState
            chart.applyOptions({
                rightPriceScale: { visible: nextStreamState.hasRenderableData },
                timeScale: { visible: nextStreamState.hasRenderableData },
            })

            if (!nextStreamState.hasRenderableData) {
                rawSeries.forEach((series) => series?.setData?.([]))
                smoothSeries.forEach((series) => series?.setData?.([]))
                rawMarkersPluginRef.current?.setMarkers?.([])
                smoothMarkersPluginRef.current?.setMarkers?.([])
                initialisedRef.current = false
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

            nextStreamState.rawSeriesPoints.forEach((points, index) => {
                syncAtmSeriesData(rawSeries[index], prevStreamState.rawSeriesPoints[index] ?? [], points)
            })
            nextStreamState.smoothSeriesPoints.forEach((points, index) => {
                syncAtmSeriesData(smoothSeries[index], prevStreamState.smoothSeriesPoints[index] ?? [], points)
            })
            rawMarkersPluginRef.current?.setMarkers?.(nextStreamState.markers)
            smoothMarkersPluginRef.current?.setMarkers?.(nextStreamState.markers)

            if (!initialisedRef.current) {
                const lastTick = findLastMarketTick(rows)
                const sessionWindow = lastTick?.timestamp
                    ? getMarketSessionWindowUnixSec(lastTick.timestamp)
                    : null
                if (sessionWindow) {
                    chart.timeScale().setVisibleRange({
                        from: sessionWindow.from as Time,
                        to: sessionWindow.to as Time,
                    })
                } else {
                    chart.timeScale().fitContent()
                }
                initialisedRef.current = true
            }
        } catch (error) {
            enterDegradedMode('update', error)
        }
    }, [applySeriesVisualState, enterDegradedMode])

    useEffect(() => {
        degradedStageRef.current = degradedStage
    }, [degradedStage])

    useEffect(() => {
        const element = containerRef.current
        if (!element || degradedStageRef.current !== null) return

        let chartRuntime: ReturnType<typeof createAtmChartRuntime>
        try {
            chartRuntime = createAtmChartRuntime(
                element,
                runtimeConfig.chartEngine,
                SERIES_CFG.map(({ color }) => ({ color })),
            )
        } catch (error) {
            enterDegradedMode('init', error)
            return
        }

        chartRef.current = chartRuntime.chart
        rawSeriesRef.current = chartRuntime.rawSeries
        smoothSeriesRef.current = chartRuntime.smoothSeries
        rawMarkersPluginRef.current = chartRuntime.rawMarkersPlugin
        smoothMarkersPluginRef.current = chartRuntime.smoothMarkersPlugin
        seriesFamilyByApiRef.current = new Map(
            SERIES_FAMILIES.flatMap((family, index) => [
                [chartRuntime.rawSeries[index], family] as const,
                [chartRuntime.smoothSeries[index], family] as const,
            ].filter(([series]) => Boolean(series)))
        )

        const handleCrosshairMove = (event: MouseEventParams<Time>) => {
            try {
                const nextFamily = resolveNextHoveredFamily({
                    event,
                    currentHoveredFamily: hoveredFamilyRef.current,
                    seriesFamilyByApi: seriesFamilyByApiRef.current,
                })
                if (hoveredFamilyRef.current === nextFamily) return
                hoveredFamilyRef.current = nextFamily
                applySeriesVisualState(displayModeRef.current, nextFamily)
            } catch (error) {
                enterDegradedMode('interaction', error)
            }
        }

        const handleMouseLeave = () => {
            try {
                if (hoveredFamilyRef.current === null) return
                hoveredFamilyRef.current = null
                applySeriesVisualState(displayModeRef.current, null)
            } catch (error) {
                enterDegradedMode('interaction', error)
            }
        }

        chartRuntime.chart.subscribeCrosshairMove(handleCrosshairMove)
        element.addEventListener('mouseleave', handleMouseLeave)
        applySeriesVisualState(displayModeRef.current, hoveredFamilyRef.current)

        const resizeObserver = new ResizeObserver((entries) => {
            try {
                const chart = chartRef.current
                if (!chart || entries.length === 0) return
                const { width, height } = entries[0].contentRect
                chart.applyOptions({ width, height })
            } catch (error) {
                enterDegradedMode('resize', error)
            }
        })
        resizeObserver.observe(element)

        return () => {
            resizeObserver.disconnect()
            try {
                chartRuntime.chart.unsubscribeCrosshairMove(handleCrosshairMove)
            } catch (error) {
                console.warn('[AtmDecayChart] Failed to unsubscribe crosshair handler.', error)
            }
            element.removeEventListener('mouseleave', handleMouseLeave)
            teardownChartRuntime()
        }
    }, [applySeriesVisualState, enterDegradedMode, teardownChartRuntime])

    useEffect(() => {
        try {
            window.localStorage.setItem(STORAGE_KEY, displayMode)
        } catch {
            // no-op
        }
    }, [displayMode])

    useEffect(() => {
        displayModeRef.current = displayMode
        if (degradedStageRef.current !== null) return
        applySeriesVisualState(displayMode, hoveredFamilyRef.current)
    }, [displayMode, applySeriesVisualState])

    useEffect(() => {
        if (document.visibilityState === 'hidden') return
        syncLatestChartState(data)
    }, [data, syncLatestChartState])

    useEffect(() => {
        const handleVisibilityChange = () => {
            if (document.visibilityState !== 'visible') return
            syncLatestChartState(data)
        }

        document.addEventListener('visibilitychange', handleVisibilityChange)
        return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
    }, [data, syncLatestChartState])

    return (
        <div className="relative w-full h-full">
            <div ref={containerRef} className="w-full h-full" style={{ touchAction: 'none' }} />
            {degradedStage ? (
                <div
                    data-testid="atm-chart-degraded"
                    className="absolute inset-0 z-30 flex items-center justify-center bg-[#090a0c]/70 text-[11px] tracking-wide text-[#fbbf24]"
                >
                    CENTER CHART DEGRADED ({degradedStage.toUpperCase()})
                </div>
            ) : null}
            <div className="absolute top-4 right-4 z-20 pointer-events-auto">
                <div className="inline-flex items-center rounded-md border border-[#27272a] bg-[#0b0c0f]/90 p-0.5">
                    {MODE_ITEMS.map((item) => {
                        const active = displayMode === item.key
                        return (
                            <button
                                key={item.key}
                                type="button"
                                onClick={() => setDisplayMode(item.key)}
                                className={`px-2 py-1 text-[10px] font-bold tracking-wider transition-colors ${
                                    active ? 'bg-[#18181b] text-[#e4e4e7]' : 'text-[#71717a] hover:text-[#d4d4d8]'
                                }`}
                            >
                                {item.label}
                            </button>
                        )
                    })}
                </div>
            </div>
        </div>
    )
})

AtmDecayChart.displayName = 'AtmDecayChart'

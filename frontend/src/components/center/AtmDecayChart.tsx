/**
 * AtmDecayChart — TradingView Lightweight Charts v5 
 * S+ 级 0DTE 衰减追踪器 (防时区坍缩 / 绝对零轴 / 阶梯渲染 / 无损 Tick)
 */
import React, { useEffect, useRef, useCallback } from 'react'
import {
    createChart,
    ColorType,
    LineStyle,
    CrosshairMode,
    LineSeries,
    LineType, // 引入阶梯线支持
    type IChartApi,
    type ISeriesApi,
    type Time,
} from 'lightweight-charts'
import type { AtmDecay } from '../../types/dashboard'

interface Props {
    data: AtmDecay[]
}

// ── Theme constants ───────────────────────────────────────────────────────────
const BG = '#060606'
const GRID = 'rgba(255,255,255,0.04)'
const CROSSHAIR = '#52525b'
const TEXT = '#71717a'
const BORDER = '#27272a'

const SERIES_CFG = [
    { key: 'straddle_pct' as const, label: 'STRADDLE', color: '#f59e0b' },
    { key: 'call_pct' as const, label: 'CALL', color: '#ef4444' },
    { key: 'put_pct' as const, label: 'PUT', color: '#10b981' },
]

// ── Helpers ───────────────────────────────────────────────────────────────────
// 获取纯粹的 Unix 时间戳 (秒)
function toUnixSec(ts: string): number {
    return Math.floor(new Date(ts).getTime() / 1000)
}

// S+ 修复 1：使用原生 API 智能转换美东时间，绝对免疫夏令时/冬令时陷阱和本地时区污染
const formatET = (time: number) => {
    const d = new Date(time * 1000)
    return d.toLocaleTimeString('en-US', {
        timeZone: 'America/New_York',
        hour12: false,
        hour: '2-digit',
        minute: '2-digit'
    })
}

function isMarketHours(ts: string): boolean {
    const d = new Date(ts)
    const etStr = d.toLocaleTimeString('en-US', {
        timeZone: 'America/New_York',
        hour: 'numeric',
        minute: 'numeric',
        hour12: false,
    })
    const [hour, minute] = etStr.split(':').map(Number)
    const timeVal = hour * 100 + minute
    // 允许 09:25 到 16:15 存在数据，避免首尾被硬切断
    return timeVal >= 925 && timeVal <= 1615
}

function buildPoints(data: AtmDecay[], key: keyof AtmDecay) {
    const seen = new Set<number>()
    const pts: { time: Time; value: number }[] = []

    data.forEach(d => {
        if (!d.timestamp || d[key] == null) return
        if (!isMarketHours(d.timestamp)) return
        const t = toUnixSec(d.timestamp)
        if (seen.has(t)) return
        seen.add(t)
        pts.push({ time: t as Time, value: (d[key] as number) * 100 })
    })

    return pts.sort((a, b) => (a.time as number) - (b.time as number))
}

// ── Component ─────────────────────────────────────────────────────────────────
export const AtmDecayChart: React.FC<Props> = ({ data }) => {
    const containerRef = useRef<HTMLDivElement>(null)
    const tooltipRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<IChartApi | null>(null)
    const seriesRefs = useRef<ISeriesApi<'Line'>[]>([])

    // S+ 修复 3：追踪已渲染的数据长度，防止丢 Tick
    const lastDataLength = useRef(0)
    const isInitialized = useRef(false)

    const initChart = useCallback(() => {
        if (!containerRef.current) return

        const chart = createChart(containerRef.current, {
            width: containerRef.current.clientWidth,
            height: containerRef.current.clientHeight,
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
                vertLine: { color: CROSSHAIR, style: LineStyle.Solid, width: 1, labelBackgroundColor: '#18181b' },
                horzLine: { color: CROSSHAIR, style: LineStyle.Solid, width: 1, labelBackgroundColor: '#18181b' },
            },
            localization: {
                timeFormatter: formatET, // 注入智能时区引擎
            },
            rightPriceScale: {
                borderColor: BORDER,
            },
            timeScale: {
                borderColor: BORDER,
                timeVisible: true,
                secondsVisible: false,
                tickMarkFormatter: formatET,
                minBarSpacing: 0.1,
            },
            handleScroll: true,
            handleScale: true,
        })

        const srs = SERIES_CFG.map(({ color }) =>
            chart.addSeries(LineSeries, {
                color,
                lineWidth: 1.5,
                lineType: LineType.Step, // S+ 修复 4：开启极度硬核的阶梯跳动
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
            }),
        )

        // S+ 修复 2：物理级绝对零轴 (不再使用假序列，直接在核心主线上挂载 PriceLine)
        srs[0].createPriceLine({
            price: 0,
            color: 'rgba(255,255,255,0.2)',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: false,
        })

        chartRef.current = chart
        seriesRefs.current = srs

        // S+ 修复 4：挂载机构级悬浮舱 (HUD Tooltip)
        chart.subscribeCrosshairMove(param => {
            const tooltip = tooltipRef.current
            if (!tooltip || !containerRef.current) return

            if (
                param.point === undefined ||
                !param.time ||
                param.point.x < 0 ||
                param.point.x > containerRef.current.clientWidth ||
                param.point.y < 0 ||
                param.point.y > containerRef.current.clientHeight
            ) {
                tooltip.style.display = 'none'
                return
            }

            const timeStr = formatET(param.time as number)

            let html = `<div class="text-[#a1a1aa] font-mono text-[11px] mb-2 border-b border-[#27272a] pb-1 text-center">${timeStr} ET</div>`

            SERIES_CFG.forEach(({ label, color }, i) => {
                const data = param.seriesData.get(srs[i]) as { value?: number } | undefined
                if (data && data.value !== undefined) {
                    const valStr = (data.value > 0 ? '+' : '') + data.value.toFixed(1) + '%'
                    html += `
                        <div class="flex items-center justify-between gap-6 leading-relaxed">
                            <span class="text-[10px] font-bold tracking-wider" style="color: ${color}">${label}</span>
                            <span class="font-mono text-[12px] font-black" style="color: ${color}">${valStr}</span>
                        </div>
                    `
                }
            })

            tooltip.innerHTML = html
            tooltip.style.display = 'block'

            // 准星定位 + 边界防溢出
            const x = param.point.x
            const y = param.point.y
            tooltip.style.left = Math.min(x + 15, containerRef.current.clientWidth - 140) + 'px'
            tooltip.style.top = Math.min(y + 15, containerRef.current.clientHeight - 80) + 'px'
        })

        const ro = new ResizeObserver(entries => {
            const { width, height } = entries[0].contentRect
            chart.applyOptions({ width, height })
        })
        ro.observe(containerRef.current)

        return () => {
            ro.disconnect()
            chart.remove()
            chartRef.current = null
            seriesRefs.current = []
        }
    }, [])

    useEffect(() => {
        const cleanup = initChart()
        return () => {
            isInitialized.current = false
            cleanup?.()
        }
    }, [initChart])

    useEffect(() => {
        if (!chartRef.current || seriesRefs.current.length === 0 || data.length === 0) return

        if (!isInitialized.current) {
            // 首次全量挂载
            SERIES_CFG.forEach(({ key }, i) => {
                const pts = buildPoints(data, key)
                if (pts.length > 0) seriesRefs.current[i].setData(pts)
            })
            chartRef.current.timeScale().fitContent()
            isInitialized.current = true
            lastDataLength.current = data.length
        } else {
            // S+ 修复 3：无缝接力增量更新，提取区间积累的所有新 Tick
            const newPointsCount = data.length - lastDataLength.current
            if (newPointsCount > 0) {
                const newTicks = data.slice(-newPointsCount)

                SERIES_CFG.forEach(({ key }, i) => {
                    newTicks.forEach(tick => {
                        if (!tick.timestamp || !isMarketHours(tick.timestamp)) return
                        const v = tick[key]
                        if (v != null) {
                            const t = toUnixSec(tick.timestamp) as Time
                            seriesRefs.current[i].update({ time: t, value: (v as number) * 100 })
                        }
                    })
                })
                lastDataLength.current = data.length
            }
        }
    }, [data])

    return (
        <div className="relative w-full h-full">
            <div
                ref={containerRef}
                className="w-full h-full"
                style={{ touchAction: 'none', userSelect: 'none', cursor: 'crosshair' }}
            />
            {/* 物理抽离的战斗机 HUD 数据舱 */}
            <div
                ref={tooltipRef}
                className="absolute z-50 bg-[#121214]/95 border border-[#27272a] rounded-[4px] shadow-2xl p-2.5 font-sans pointer-events-none transition-none"
                style={{ display: 'none', minWidth: '130px' }}
            >
            </div>
        </div>
    )
}
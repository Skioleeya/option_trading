import { type MouseEventParams, type Time } from 'lightweight-charts'

export type DisplayMode = 'smoothed' | 'raw' | 'both'
export type SeriesFamily = 'straddle' | 'call' | 'put'
export type SeriesLayer = 'raw' | 'smooth'
type CrosshairPoint = MouseEventParams<Time>['point']

export interface SeriesVisualState {
    visible: boolean
    color: string
    lineWidth: number
    priceLineVisible: boolean
    lastValueVisible: boolean
    crosshairMarkerVisible: boolean
    crosshairMarkerRadius: number
    crosshairMarkerBackgroundColor: string
}

interface ResolveHoveredFamilyParams {
    event: MouseEventParams<Time>
    seriesFamilyByApi: Map<unknown, SeriesFamily>
}

interface ResolveNextHoveredFamilyParams extends ResolveHoveredFamilyParams {
    currentHoveredFamily?: SeriesFamily | null
    inferredFamily?: SeriesFamily | null
}

interface ResolveHoveredFamilyAfterDataRefreshParams {
    hasRenderableData: boolean
    currentHoveredFamily: SeriesFamily | null
}

interface BuildSeriesVisualStateParams {
    displayMode: DisplayMode
    hoveredFamily: SeriesFamily | null
    family: SeriesFamily
    layer: SeriesLayer
    baseColor: string
}

function hexToRgba(hex: string, alpha: number): string {
    const h = hex.replace('#', '')
    if (h.length !== 6) return hex
    const r = parseInt(h.slice(0, 2), 16)
    const g = parseInt(h.slice(2, 4), 16)
    const b = parseInt(h.slice(4, 6), 16)
    return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export function resolveHoveredFamily({
    event,
    seriesFamilyByApi,
}: ResolveHoveredFamilyParams): SeriesFamily | null {
    if (!hasValidCrosshairPoint(event.point) || !event.hoveredSeries) return null
    return seriesFamilyByApi.get(event.hoveredSeries) ?? null
}

export function hasValidCrosshairPoint(point: CrosshairPoint): boolean {
    if (!point) return false
    return Number.isFinite(point.x as number) && Number.isFinite(point.y as number)
}

export function resolveNextHoveredFamily({
    event,
    seriesFamilyByApi,
}: ResolveNextHoveredFamilyParams): SeriesFamily | null {
    if (!hasValidCrosshairPoint(event.point)) return null
    return resolveHoveredFamily({ event, seriesFamilyByApi })
}

export function resolveHoveredFamilyAfterDataRefresh({
    hasRenderableData,
    currentHoveredFamily,
}: ResolveHoveredFamilyAfterDataRefreshParams): SeriesFamily | null {
    if (!hasRenderableData) return null
    return currentHoveredFamily
}

export function buildSeriesVisualState({
    displayMode,
    hoveredFamily,
    family,
    layer,
    baseColor,
}: BuildSeriesVisualStateParams): SeriesVisualState {
    const baseVisible = layer === 'raw'
        ? displayMode === 'raw' || displayMode === 'both'
        : displayMode === 'smoothed' || displayMode === 'both'
    const isFocus = hoveredFamily !== null && family === hoveredFamily
    const isDeemphasized = hoveredFamily !== null && !isFocus

    if (layer === 'raw') {
        if (!baseVisible) {
            return {
                visible: false,
                color: baseColor,
                lineWidth: 1,
                priceLineVisible: false,
                lastValueVisible: false,
                crosshairMarkerVisible: false,
                crosshairMarkerRadius: 3,
                crosshairMarkerBackgroundColor: baseColor,
            }
        }

        let color = displayMode === 'both' ? hexToRgba(baseColor, 0.35) : baseColor
        let lineWidth = 1
        let priceLineVisible = displayMode === 'raw'
        let lastValueVisible = displayMode === 'raw'

        if (isFocus) {
            color = displayMode === 'both' ? hexToRgba(baseColor, 0.82) : baseColor
        } else if (isDeemphasized) {
            return {
                visible: false,
                color,
                lineWidth,
                priceLineVisible: false,
                lastValueVisible: false,
                crosshairMarkerVisible: false,
                crosshairMarkerRadius: 3,
                crosshairMarkerBackgroundColor: baseColor,
            }
        }

        return {
            visible: true,
            color,
            lineWidth,
            priceLineVisible,
            lastValueVisible,
            crosshairMarkerVisible: false,
            crosshairMarkerRadius: 3,
            crosshairMarkerBackgroundColor: baseColor,
        }
    }

    if (!baseVisible) {
        return {
            visible: false,
            color: baseColor,
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
            crosshairMarkerRadius: 3,
            crosshairMarkerBackgroundColor: baseColor,
        }
    }

    let color = baseColor
    let lineWidth = 2
    let priceLineVisible = displayMode !== 'raw'
    let lastValueVisible = displayMode !== 'raw'
    let crosshairMarkerVisible = displayMode !== 'raw'
    let crosshairMarkerRadius = 3

    if (isFocus) {
        color = baseColor
        crosshairMarkerVisible = true
    } else if (isDeemphasized) {
        return {
            visible: false,
            color,
            lineWidth,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
            crosshairMarkerRadius: 3,
            crosshairMarkerBackgroundColor: baseColor,
        }
    }

    return {
        visible: true,
        color,
        lineWidth,
        priceLineVisible,
        lastValueVisible,
        crosshairMarkerVisible,
        crosshairMarkerRadius,
        crosshairMarkerBackgroundColor: baseColor,
    }
}

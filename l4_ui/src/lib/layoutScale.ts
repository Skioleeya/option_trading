export interface ViewportSize {
    width: number
    height: number
}

export type MonitorLayoutProfile = 'primary_standard' | 'secondary_compact'

export interface LayoutScaleState {
    scale: number
    percent: number
    profile: MonitorLayoutProfile
}

export const L4_LAYOUT_BASE_WIDTH = 1920
export const L4_LAYOUT_BASE_HEIGHT = 1080
export const L4_LAYOUT_MIN_SCALE = 0.5
export const L4_LAYOUT_MAX_SCALE = 1.25
export const L4_SECONDARY_PROFILE_MAX_WIDTH = 1366
export const L4_SECONDARY_PROFILE_MAX_HEIGHT = 768

interface LayoutProfileTokens {
    leftWidth: number
    rightWidth: number
    headerHeight: number
    headerCenterGap: number
    headerClusterGap: number
    headerInlineGap: number
    headerSidePad: number
    headerTitleFont: number
    headerMetaFont: number
    headerValueFont: number
    headerBadgeFont: number
    headerMicroFont: number
    headerBadgePadX: number
    headerBadgePadY: number
    headerBadgeRowGap: number
    headerIndicatorSize: number
    dividerHeight: number
    panelPad: number
    panelGap: number
    cardPad: number
    compactCardPad: number
    cardRadius: number
    gexBarWidth: number
    gexBarHeight: number
    gexPadX: number
    overlayOffset: number
    gexBottomOffset: number
    overlayPad: number
    metricFont: number
    labelFont: number
    smallFont: number
    tinyFont: number
    triadValueFont: number
    wallRowHeight: number
    wallLabelWidth: number
    wallStateWidth: number
    rowAccentWidth: number
}

const PROFILE_TOKENS: Record<MonitorLayoutProfile, LayoutProfileTokens> = {
    primary_standard: {
        leftWidth: 272,
        rightWidth: 296,
        headerHeight: 36,
        headerCenterGap: 18,
        headerClusterGap: 12,
        headerInlineGap: 6,
        headerSidePad: 10,
        headerTitleFont: 11,
        headerMetaFont: 10,
        headerValueFont: 12,
        headerBadgeFont: 9,
        headerMicroFont: 7,
        headerBadgePadX: 6,
        headerBadgePadY: 1,
        headerBadgeRowGap: 4,
        headerIndicatorSize: 8,
        dividerHeight: 12,
        panelPad: 8,
        panelGap: 6,
        cardPad: 6,
        compactCardPad: 4,
        cardRadius: 4,
        gexBarWidth: 520,
        gexBarHeight: 36,
        gexPadX: 16,
        overlayOffset: 12,
        gexBottomOffset: 24,
        overlayPad: 12,
        metricFont: 10,
        labelFont: 9,
        smallFont: 8,
        tinyFont: 7,
        triadValueFont: 18,
        wallRowHeight: 22,
        wallLabelWidth: 26,
        wallStateWidth: 68,
        rowAccentWidth: 4,
    },
    secondary_compact: {
        leftWidth: 240,
        rightWidth: 264,
        headerHeight: 34,
        headerCenterGap: 10,
        headerClusterGap: 8,
        headerInlineGap: 4,
        headerSidePad: 8,
        headerTitleFont: 10,
        headerMetaFont: 9,
        headerValueFont: 11,
        headerBadgeFont: 8,
        headerMicroFont: 7,
        headerBadgePadX: 5,
        headerBadgePadY: 1,
        headerBadgeRowGap: 3,
        headerIndicatorSize: 6,
        dividerHeight: 10,
        panelPad: 5,
        panelGap: 4,
        cardPad: 4,
        compactCardPad: 2,
        cardRadius: 3,
        gexBarWidth: 440,
        gexBarHeight: 34,
        gexPadX: 12,
        overlayOffset: 8,
        gexBottomOffset: 16,
        overlayPad: 10,
        metricFont: 9,
        labelFont: 8,
        smallFont: 8,
        tinyFont: 7,
        triadValueFont: 15,
        wallRowHeight: 20,
        wallLabelWidth: 24,
        wallStateWidth: 60,
        rowAccentWidth: 3,
    },
}

function toPx(value: number): string {
    const rounded = Math.round(value * 1000) / 1000
    return `${rounded}px`
}

export function sanitizeDimension(value: number | undefined): number {
    if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) {
        return 1
    }
    return value
}

export function clampLayoutScale(value: number): number {
    return Math.min(L4_LAYOUT_MAX_SCALE, Math.max(L4_LAYOUT_MIN_SCALE, value))
}

export function resolveLayoutProfile(viewport: ViewportSize): MonitorLayoutProfile {
    const width = sanitizeDimension(viewport.width)
    const height = sanitizeDimension(viewport.height)
    if (width <= L4_SECONDARY_PROFILE_MAX_WIDTH || height <= L4_SECONDARY_PROFILE_MAX_HEIGHT) {
        return 'secondary_compact'
    }
    return 'primary_standard'
}

export function computeLayoutScale(viewport: ViewportSize): LayoutScaleState {
    const widthRatio = sanitizeDimension(viewport.width) / L4_LAYOUT_BASE_WIDTH
    const heightRatio = sanitizeDimension(viewport.height) / L4_LAYOUT_BASE_HEIGHT
    const scale = clampLayoutScale(Math.min(widthRatio, heightRatio))
    return {
        scale,
        percent: Math.round(scale * 100),
        profile: resolveLayoutProfile(viewport),
    }
}

export function buildLayoutScaleVars(scale: number, profile: MonitorLayoutProfile): Record<string, string> {
    const tokens = PROFILE_TOKENS[profile]
    const headerGap = tokens.headerCenterGap
    const headerClusterGap = tokens.headerClusterGap
    const headerInlineGap = tokens.headerInlineGap
    const headerPadX = tokens.headerSidePad
    const headerTitleLineHeight = tokens.headerTitleFont + 2
    const headerMetaLineHeight = tokens.headerMetaFont + 2
    const headerValueLineHeight = tokens.headerValueFont + 2
    const headerBadgeLineHeight = tokens.headerBadgeFont + 1
    const headerMicroLineHeight = Math.max(tokens.headerMicroFont + 1, 8)
    const headerDotSm = Math.max(4, tokens.headerIndicatorSize)
    const headerDotXs = Math.max(4, tokens.headerIndicatorSize - 2)
    return {
        '--l4-scale': scale.toString(),
        '--l4-header-h': toPx(tokens.headerHeight),
        '--l4-left-w': toPx(tokens.leftWidth),
        '--l4-right-w': toPx(tokens.rightWidth),
        '--l4-gex-bar-w': toPx(tokens.gexBarWidth),
        '--l4-gex-bar-h': toPx(tokens.gexBarHeight),
        '--l4-gex-pad-x': toPx(tokens.gexPadX),
        '--l4-space-3': toPx(tokens.overlayOffset),
        '--l4-space-8': toPx(tokens.gexBottomOffset),
        '--l4-overlay-card-pad': toPx(tokens.overlayPad),
        '--l4-radius-xl': toPx(tokens.overlayPad),
        '--l4-divider-h': toPx(tokens.dividerHeight),
        '--l4-font-7': toPx(tokens.tinyFont),
        '--l4-font-8': toPx(tokens.smallFont),
        '--l4-font-9': toPx(tokens.labelFont),
        '--l4-font-10': toPx(tokens.metricFont),
        '--l4-font-11': toPx(tokens.headerTitleFont),
        '--l4-font-12': toPx(tokens.headerValueFont),
        '--l4-font-13': toPx(tokens.headerValueFont + 1),
        '--l4-icon-xs': toPx(tokens.metricFont),
        '--l4-icon-sm': toPx(tokens.headerValueFont),
        '--l4-icon-md': toPx(tokens.headerValueFont + 2),
        '--l4-dot-sm': toPx(tokens.headerIndicatorSize),
        '--l4-dot-xs': toPx(Math.max(tokens.headerIndicatorSize - 2, 4)),
        '--l4-header-gap': toPx(headerGap),
        '--l4-header-cluster-gap': toPx(headerClusterGap),
        '--l4-header-inline-gap': toPx(headerInlineGap),
        '--l4-header-pad-x': toPx(headerPadX),
        '--l4-header-meta-font': toPx(tokens.headerMetaFont),
        '--l4-header-title-font': toPx(tokens.headerTitleFont),
        '--l4-header-value-font': toPx(tokens.headerValueFont),
        '--l4-header-title-line-h': toPx(headerTitleLineHeight),
        '--l4-header-meta-line-h': toPx(headerMetaLineHeight),
        '--l4-header-value-line-h': toPx(headerValueLineHeight),
        '--l4-header-badge-font': toPx(tokens.headerBadgeFont),
        '--l4-header-micro-font': toPx(tokens.headerMicroFont),
        '--l4-header-badge-line-h': toPx(headerBadgeLineHeight),
        '--l4-header-micro-line-h': toPx(headerMicroLineHeight),
        '--l4-header-badge-pad-x': toPx(tokens.headerBadgePadX),
        '--l4-header-badge-pad-y': toPx(tokens.headerBadgePadY),
        '--l4-header-badge-row-gap': toPx(tokens.headerBadgeRowGap),
        '--l4-header-icon-xs': toPx(tokens.metricFont),
        '--l4-header-dot-sm': toPx(headerDotSm),
        '--l4-header-dot-xs': toPx(headerDotXs),
        '--l4-panel-pad': toPx(tokens.panelPad),
        '--l4-panel-gap': toPx(tokens.panelGap),
        '--l4-card-pad': toPx(tokens.cardPad),
        '--l4-card-pad-tight': toPx(tokens.compactCardPad),
        '--l4-card-radius': toPx(tokens.cardRadius),
        '--l4-triad-value-font': toPx(tokens.triadValueFont),
        '--l4-wall-row-h': toPx(tokens.wallRowHeight),
        '--l4-wall-label-w': toPx(tokens.wallLabelWidth),
        '--l4-wall-state-w': toPx(tokens.wallStateWidth),
        '--l4-row-accent-w': toPx(tokens.rowAccentWidth),
    }
}

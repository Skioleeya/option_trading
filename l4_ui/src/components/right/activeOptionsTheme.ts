export type ActiveFlowDirection = 'BULLISH' | 'BEARISH' | 'NEUTRAL'
export type ActiveFlowIntensity = 'EXTREME' | 'HIGH' | 'MODERATE' | 'LOW'
export const ACTIVE_OPTIONS_FIXED_ROWS = 5

export const ACTIVE_OPTIONS_FLOW_COLOR_BY_DIRECTION: Record<ActiveFlowDirection, string> = {
    BULLISH: 'text-accent-red',
    BEARISH: 'text-accent-green',
    NEUTRAL: 'text-text-secondary',
}

export const ACTIVE_OPTIONS_ALLOWED_FLOW_COLOR = new Set<string>([
    'text-accent-red',
    'text-accent-green',
    'text-text-secondary',
])

export const ACTIVE_OPTIONS_FLOW_DIRECTION_BY_COLOR: Record<string, ActiveFlowDirection> = {
    'text-accent-red': 'BULLISH',
    'text-accent-green': 'BEARISH',
    'text-text-secondary': 'NEUTRAL',
}

export const ACTIVE_OPTIONS_FLOW_INTENSITY_SET = new Set<string>([
    'EXTREME',
    'HIGH',
    'MODERATE',
    'LOW',
])

export const ACTIVE_OPTIONS_FLOW_GLOW_BY_DIRECTION_AND_INTENSITY: Record<ActiveFlowDirection, Record<ActiveFlowIntensity, string>> = {
    BULLISH: {
        EXTREME: 'shadow-[0_0_12px_rgba(255,77,79,0.6)] animate-pulse',
        HIGH: 'shadow-[0_0_8px_rgba(255,77,79,0.35)]',
        MODERATE: '',
        LOW: '',
    },
    BEARISH: {
        EXTREME: 'shadow-[0_0_12px_rgba(16,185,129,0.6)] animate-pulse',
        HIGH: 'shadow-[0_0_8px_rgba(16,185,129,0.35)]',
        MODERATE: '',
        LOW: '',
    },
    NEUTRAL: {
        EXTREME: '',
        HIGH: '',
        MODERATE: '',
        LOW: '',
    },
}

export const ACTIVE_OPTIONS_SWEEP_GLOW = 'shadow-[0_0_15px_rgba(255,255,255,0.7)] animate-pulse'

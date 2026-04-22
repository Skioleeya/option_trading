import type { SkewDynamicsState } from '../../types/dashboard'

export const SKEW_DYNAMICS_DEFAULT_STATE = 'NEUTRAL'
export const SKEW_DYNAMICS_UNAVAILABLE_STATE = 'UNAVAILABLE'
export const SKEW_DYNAMICS_DEFAULT_VALUE = '—'
export const SKEW_DYNAMICS_UNAVAILABLE_VALUE = 'N/A'
export const SKEW_DYNAMICS_VALUE_DECIMALS = 2

export const SKEW_DYNAMICS_ALLOWED_STATES = new Set([
    'SPECULATIVE',
    'DEFENSIVE',
    SKEW_DYNAMICS_DEFAULT_STATE,
    SKEW_DYNAMICS_UNAVAILABLE_STATE,
])

export const SKEW_DYNAMICS_THEME: Record<string, Pick<SkewDynamicsState, 'color_class' | 'border_class' | 'bg_class' | 'shadow_class' | 'badge'>> = {
    SPECULATIVE: {
        color_class: 'text-accent-red',
        border_class: 'border-accent-red/40',
        bg_class: 'bg-accent-red/5',
        shadow_class: 'shadow-none',
        badge: 'badge-red',
    },
    DEFENSIVE: {
        color_class: 'text-accent-green',
        border_class: 'border-accent-green/40',
        bg_class: 'bg-accent-green/5',
        shadow_class: 'shadow-none',
        badge: 'badge-green',
    },
    NEUTRAL: {
        color_class: 'text-text-primary',
        border_class: 'border-bg-border',
        bg_class: 'bg-bg-card',
        shadow_class: 'shadow-none',
        badge: 'badge-neutral',
    },
    UNAVAILABLE: {
        color_class: 'text-text-secondary',
        border_class: 'border-bg-border',
        bg_class: 'bg-bg-card',
        shadow_class: 'shadow-none',
        badge: 'badge-neutral',
    },
}

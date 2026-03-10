import type { SkewDynamicsState } from '../../types/dashboard'

export const SKEW_DYNAMICS_ZERO: SkewDynamicsState = {
    value: '—',
    state_label: 'NEUTRAL',
    color_class: 'text-text-primary',
    border_class: 'border-bg-border',
    bg_class: 'bg-bg-card',
    shadow_class: 'shadow-none',
    badge: 'badge-neutral',
}

const SKEW_THEME: Record<string, Pick<SkewDynamicsState, 'color_class' | 'border_class' | 'bg_class' | 'shadow_class' | 'badge'>> = {
    SPECULATIVE: {
        color_class: 'text-accent-red',
        border_class: 'border-accent-red/40',
        bg_class: 'bg-accent-red/5',
        shadow_class: 'shadow-[0_0_10px_rgba(239,68,68,0.12)]',
        badge: 'badge-red',
    },
    DEFENSIVE: {
        color_class: 'text-accent-green',
        border_class: 'border-accent-green/40',
        bg_class: 'bg-accent-green/5',
        shadow_class: 'shadow-[0_0_10px_rgba(16,185,129,0.12)]',
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

export function normalizeSkewDynamicsState(input: unknown): SkewDynamicsState {
    if (!input || typeof input !== 'object') return SKEW_DYNAMICS_ZERO
    const raw = input as Partial<SkewDynamicsState>
    const stateLabel = typeof raw.state_label === 'string' && raw.state_label.trim()
        ? raw.state_label.trim().toUpperCase()
        : SKEW_DYNAMICS_ZERO.state_label
    const theme = SKEW_THEME[stateLabel] ?? SKEW_THEME.NEUTRAL

    return {
        value: typeof raw.value === 'string' && raw.value.trim() ? raw.value : SKEW_DYNAMICS_ZERO.value,
        state_label: stateLabel,
        color_class: theme.color_class,
        border_class: theme.border_class,
        bg_class: theme.bg_class,
        shadow_class: theme.shadow_class,
        badge: theme.badge,
    }
}

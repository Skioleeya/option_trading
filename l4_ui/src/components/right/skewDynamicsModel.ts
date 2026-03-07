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

export function normalizeSkewDynamicsState(input: unknown): SkewDynamicsState {
    if (!input || typeof input !== 'object') return SKEW_DYNAMICS_ZERO
    const raw = input as Partial<SkewDynamicsState>
    return {
        value: typeof raw.value === 'string' && raw.value.trim() ? raw.value : SKEW_DYNAMICS_ZERO.value,
        state_label: typeof raw.state_label === 'string' && raw.state_label.trim()
            ? raw.state_label
            : SKEW_DYNAMICS_ZERO.state_label,
        color_class: typeof raw.color_class === 'string' && raw.color_class.trim()
            ? raw.color_class
            : SKEW_DYNAMICS_ZERO.color_class,
        border_class: typeof raw.border_class === 'string' && raw.border_class.trim()
            ? raw.border_class
            : SKEW_DYNAMICS_ZERO.border_class,
        bg_class: typeof raw.bg_class === 'string' && raw.bg_class.trim()
            ? raw.bg_class
            : SKEW_DYNAMICS_ZERO.bg_class,
        shadow_class: typeof raw.shadow_class === 'string' && raw.shadow_class.trim()
            ? raw.shadow_class
            : SKEW_DYNAMICS_ZERO.shadow_class,
        badge: typeof raw.badge === 'string' && raw.badge.trim()
            ? raw.badge
            : SKEW_DYNAMICS_ZERO.badge,
    }
}

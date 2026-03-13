import type { SkewDynamicsState } from '../../types/dashboard'
import {
    SKEW_DYNAMICS_ALLOWED_STATES,
    SKEW_DYNAMICS_DEFAULT_STATE,
    SKEW_DYNAMICS_DEFAULT_VALUE,
    SKEW_DYNAMICS_THEME,
    SKEW_DYNAMICS_UNAVAILABLE_STATE,
    SKEW_DYNAMICS_UNAVAILABLE_VALUE,
    SKEW_DYNAMICS_VALUE_DECIMALS,
} from './skewDynamicsTheme'

export const SKEW_DYNAMICS_ZERO: SkewDynamicsState = {
    value: SKEW_DYNAMICS_DEFAULT_VALUE,
    state_label: SKEW_DYNAMICS_DEFAULT_STATE,
    ...SKEW_DYNAMICS_THEME[SKEW_DYNAMICS_DEFAULT_STATE],
}

function normalizeStateLabel(raw: unknown): string {
    const text = typeof raw === 'string' ? raw.trim().toUpperCase() : ''
    if (SKEW_DYNAMICS_ALLOWED_STATES.has(text)) {
        return text
    }
    return SKEW_DYNAMICS_DEFAULT_STATE
}

function normalizeValue(raw: unknown, stateLabel: string): string {
    if (stateLabel === SKEW_DYNAMICS_UNAVAILABLE_STATE) {
        return SKEW_DYNAMICS_UNAVAILABLE_VALUE
    }

    if (typeof raw === 'number' && Number.isFinite(raw)) {
        return raw.toFixed(SKEW_DYNAMICS_VALUE_DECIMALS)
    }

    if (typeof raw === 'string') {
        const text = raw.trim()
        if (!text) return SKEW_DYNAMICS_DEFAULT_VALUE
        if (text.toUpperCase() === SKEW_DYNAMICS_UNAVAILABLE_VALUE) {
            return SKEW_DYNAMICS_UNAVAILABLE_VALUE
        }
        const parsed = Number(text)
        if (Number.isFinite(parsed)) {
            return parsed.toFixed(SKEW_DYNAMICS_VALUE_DECIMALS)
        }
        return text
    }

    return SKEW_DYNAMICS_DEFAULT_VALUE
}

export function normalizeSkewDynamicsState(input: unknown): SkewDynamicsState {
    if (!input || typeof input !== 'object') return SKEW_DYNAMICS_ZERO
    const raw = input as Partial<SkewDynamicsState>
    const stateLabel = normalizeStateLabel(raw.state_label)
    const theme = SKEW_DYNAMICS_THEME[stateLabel]

    return {
        value: normalizeValue(raw.value, stateLabel),
        state_label: stateLabel,
        color_class: theme.color_class,
        border_class: theme.border_class,
        bg_class: theme.bg_class,
        shadow_class: theme.shadow_class,
        badge: theme.badge,
    }
}

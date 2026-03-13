import type { TacticalTriadCard, TacticalTriadState } from '../../types/dashboard'

export type TacticalTriadTone = 'bull' | 'bear' | 'info' | 'warn' | 'neutral'
export type TacticalTriadLeg = keyof TacticalTriadState

export const TACTICAL_TRIAD_CARD_BASE = {
    color_class: 'text-text-secondary',
    border_class: 'border-bg-border',
    bg_class: 'bg-bg-card',
    shadow_class: 'shadow-none',
    animation: '',
    sub_intensity: 'LOW',
    sub_label: 'NEUTRAL',
} as const

export const TACTICAL_TRIAD_ZERO: TacticalTriadState = {
    vrp: { ...TACTICAL_TRIAD_CARD_BASE, value: '—', state_label: 'VRP' },
    charm: { ...TACTICAL_TRIAD_CARD_BASE, value: '—', state_label: 'STABLE', multiplier: null, sub_label: 'STABLE' },
    svol: { ...TACTICAL_TRIAD_CARD_BASE, value: '—', state_label: 'S-VOL' },
}

export const TACTICAL_TRIAD_CARD_THEME: Record<TacticalTriadTone, Pick<TacticalTriadCard, 'color_class' | 'border_class' | 'bg_class' | 'shadow_class'>> = {
    bull: {
        color_class: 'text-accent-red',
        border_class: 'border-accent-red/40',
        bg_class: 'bg-accent-red/5',
        shadow_class: 'shadow-none',
    },
    bear: {
        color_class: 'text-accent-green',
        border_class: 'border-accent-green/40',
        bg_class: 'bg-accent-green/5',
        shadow_class: 'shadow-none',
    },
    info: {
        color_class: 'text-accent-cyan',
        border_class: 'border-accent-cyan/40',
        bg_class: 'bg-accent-cyan/5',
        shadow_class: 'shadow-none',
    },
    warn: {
        color_class: 'text-accent-amber',
        border_class: 'border-accent-amber/40',
        bg_class: 'bg-accent-amber/5',
        shadow_class: 'shadow-none',
    },
    neutral: {
        color_class: 'text-text-primary',
        border_class: 'border-bg-border',
        bg_class: 'bg-bg-card',
        shadow_class: 'shadow-none',
    },
}

export const TACTICAL_TRIAD_INTENSITY_WHITELIST = new Set(['EXTREME', 'HIGH', 'MEDIUM', 'LOW'])
export const TACTICAL_TRIAD_PULSE_INTENSITIES = new Set(['EXTREME', 'HIGH'])

export const TACTICAL_TRIAD_STATE_TONE_BY_LEG: Record<TacticalTriadLeg, Record<string, TacticalTriadTone>> = {
    vrp: {
        BULL: 'bull',
        BUY: 'bull',
        BEAR: 'bear',
        SELL: 'bear',
    },
    charm: {
        RISING: 'bull',
        DECAYING: 'bear',
    },
    svol: {
        TOXIC: 'bull',
        FLIP: 'warn',
        GRIND: 'info',
    },
}

export const TACTICAL_TRIAD_SUBLABEL_TONE_BY_LEG: Record<TacticalTriadLeg, Record<string, TacticalTriadTone>> = {
    vrp: {
        BREAKOUT: 'bull',
        'WASH OUT': 'bear',
    },
    charm: {
        REVERSAL: 'bull',
        ACCELERATING: 'bear',
    },
    svol: {
        'TOXIC DRAG': 'bull',
        'FLIP RISK': 'warn',
        MOMENTUM: 'info',
    },
}

export const TACTICAL_TRIAD_SVOL_PLACEHOLDER_STATE = 'S-VOL'
export const TACTICAL_TRIAD_SVOL_DEFAULT_STATE = 'STBL'
export const TACTICAL_TRIAD_SVOL_STATE_BY_SUBLABEL: Record<string, string> = {
    'TOXIC DRAG': 'TOXIC',
    'FLIP RISK': 'FLIP',
    MOMENTUM: 'GRIND',
}

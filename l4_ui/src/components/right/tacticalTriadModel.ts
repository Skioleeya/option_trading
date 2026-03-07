import type { TacticalTriadCard, TacticalTriadState } from '../../types/dashboard'

const CARD_BASE = {
    color_class: 'text-text-secondary',
    border_class: 'border-bg-border',
    bg_class: 'bg-bg-card',
    shadow_class: 'shadow-none',
    animation: '',
    sub_intensity: 'LOW',
    sub_label: 'NEUTRAL',
} as const

export const TACTICAL_TRIAD_ZERO: TacticalTriadState = {
    vrp: { ...CARD_BASE, value: '—', state_label: 'VRP' },
    charm: { ...CARD_BASE, value: '—', state_label: 'STABLE', multiplier: null, sub_label: 'STABLE' },
    svol: { ...CARD_BASE, value: '—', state_label: 'S-VOL' },
}

function normalizeCard(
    input: unknown,
    fallback: TacticalTriadCard
): TacticalTriadCard {
    if (!input || typeof input !== 'object') return fallback
    const raw = input as Partial<TacticalTriadCard>
    return {
        value: raw.value ?? fallback.value,
        state_label: raw.state_label ?? fallback.state_label,
        color_class: raw.color_class ?? fallback.color_class,
        border_class: raw.border_class ?? fallback.border_class,
        bg_class: raw.bg_class ?? fallback.bg_class,
        shadow_class: raw.shadow_class ?? fallback.shadow_class,
        animation: raw.animation ?? fallback.animation,
        multiplier: raw.multiplier ?? fallback.multiplier ?? null,
        sub_intensity: raw.sub_intensity ?? fallback.sub_intensity,
        sub_label: raw.sub_label ?? fallback.sub_label,
    }
}

export function normalizeTacticalTriadState(input: unknown): TacticalTriadState {
    if (!input || typeof input !== 'object') return TACTICAL_TRIAD_ZERO
    const raw = input as Partial<TacticalTriadState>
    return {
        vrp: normalizeCard(raw.vrp, TACTICAL_TRIAD_ZERO.vrp),
        charm: normalizeCard(raw.charm, TACTICAL_TRIAD_ZERO.charm),
        svol: normalizeCard(raw.svol, TACTICAL_TRIAD_ZERO.svol),
    }
}

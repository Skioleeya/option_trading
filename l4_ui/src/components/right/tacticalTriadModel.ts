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

type CardTone = 'bull' | 'bear' | 'info' | 'neutral'

const CARD_THEME: Record<CardTone, Pick<TacticalTriadCard, 'color_class' | 'border_class' | 'bg_class' | 'shadow_class'>> = {
    bull: {
        color_class: 'text-accent-red',
        border_class: 'border-accent-red/40',
        bg_class: 'bg-accent-red/5',
        shadow_class: 'shadow-[0_0_10px_rgba(239,68,68,0.12)]',
    },
    bear: {
        color_class: 'text-accent-green',
        border_class: 'border-accent-green/40',
        bg_class: 'bg-accent-green/5',
        shadow_class: 'shadow-[0_0_10px_rgba(16,185,129,0.12)]',
    },
    info: {
        color_class: 'text-accent-cyan',
        border_class: 'border-accent-cyan/40',
        bg_class: 'bg-accent-cyan/5',
        shadow_class: 'shadow-none',
    },
    neutral: {
        color_class: 'text-text-primary',
        border_class: 'border-bg-border',
        bg_class: 'bg-bg-card',
        shadow_class: 'shadow-none',
    },
}

export const TACTICAL_TRIAD_ZERO: TacticalTriadState = {
    vrp: { ...CARD_BASE, value: '—', state_label: 'VRP' },
    charm: { ...CARD_BASE, value: '—', state_label: 'STABLE', multiplier: null, sub_label: 'STABLE' },
    svol: { ...CARD_BASE, value: '—', state_label: 'S-VOL' },
}

function normalizeIntensity(raw: unknown, fallback: string): string {
    const text = typeof raw === 'string' ? raw.trim().toUpperCase() : ''
    if (text === 'EXTREME' || text === 'HIGH' || text === 'MODERATE' || text === 'LOW') {
        return text
    }
    return fallback
}

function classifyTone(stateLabel: string, subLabel: string): CardTone {
    const state = stateLabel.toUpperCase()
    const sub = subLabel.toUpperCase()
    const text = `${state} ${sub}`
    if (text.includes('BULL') || text.includes('RISING') || text.includes('EXPANSION') || text.includes('SPECULATIVE')) {
        return 'bull'
    }
    if (text.includes('BEAR') || text.includes('DEFENSIVE') || text.includes('CONTRACTION') || text.includes('DROP')) {
        return 'bear'
    }
    if (text.includes('GRIND') || text.includes('MOMENTUM') || text.includes('FLOW')) {
        return 'info'
    }
    return 'neutral'
}

function normalizeCard(
    input: unknown,
    fallback: TacticalTriadCard
): TacticalTriadCard {
    if (!input || typeof input !== 'object') return fallback
    const raw = input as Partial<TacticalTriadCard>
    const stateLabel = raw.state_label ?? fallback.state_label
    const subLabel = raw.sub_label ?? fallback.sub_label
    const subIntensity = normalizeIntensity(raw.sub_intensity, fallback.sub_intensity)
    const tone = classifyTone(stateLabel, subLabel)
    const theme = CARD_THEME[tone]

    return {
        value: raw.value ?? fallback.value,
        state_label: stateLabel,
        color_class: theme.color_class,
        border_class: theme.border_class,
        bg_class: theme.bg_class,
        shadow_class: theme.shadow_class,
        animation: subIntensity === 'HIGH' || subIntensity === 'EXTREME' ? 'animate-pulse' : '',
        multiplier: raw.multiplier ?? fallback.multiplier ?? null,
        sub_intensity: subIntensity,
        sub_label: subLabel,
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

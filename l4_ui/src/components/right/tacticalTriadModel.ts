import type { TacticalTriadCard, TacticalTriadState } from '../../types/dashboard'
import {
    TACTICAL_TRIAD_CARD_THEME,
    TACTICAL_TRIAD_INTENSITY_WHITELIST,
    TACTICAL_TRIAD_PULSE_INTENSITIES,
    TACTICAL_TRIAD_STATE_TONE_BY_LEG,
    TACTICAL_TRIAD_SVOL_DEFAULT_STATE,
    TACTICAL_TRIAD_SVOL_PLACEHOLDER_STATE,
    TACTICAL_TRIAD_SVOL_STATE_BY_SUBLABEL,
    TACTICAL_TRIAD_SUBLABEL_TONE_BY_LEG,
    TACTICAL_TRIAD_ZERO,
    type TacticalTriadLeg,
    type TacticalTriadTone,
} from './tacticalTriadTheme'

function normalizeLabel(raw: unknown): string {
    const text = typeof raw === 'string' ? raw : ''
    const normalized = text.trim().toUpperCase().replace(/\s+/g, ' ')
    return normalized
}

function normalizeIntensity(raw: unknown, fallback: string): string {
    const text = normalizeLabel(raw)
    if (TACTICAL_TRIAD_INTENSITY_WHITELIST.has(text)) {
        return text
    }
    return fallback
}

function classifyTone(leg: TacticalTriadLeg, stateLabel: string, subLabel: string): TacticalTriadTone {
    const state = normalizeLabel(stateLabel)
    const sub = normalizeLabel(subLabel)
    const stateTone = TACTICAL_TRIAD_STATE_TONE_BY_LEG[leg][state]
    if (stateTone) return stateTone
    const subTone = TACTICAL_TRIAD_SUBLABEL_TONE_BY_LEG[leg][sub]
    return subTone ?? 'neutral'
}

function resolveStateLabel(
    leg: TacticalTriadLeg,
    stateLabel: string,
    subLabel: string,
    value: unknown
): string {
    if (leg !== 'svol' || stateLabel !== TACTICAL_TRIAD_SVOL_PLACEHOLDER_STATE) {
        return stateLabel
    }

    const inferredFromSub = TACTICAL_TRIAD_SVOL_STATE_BY_SUBLABEL[subLabel]
    if (inferredFromSub) {
        return inferredFromSub
    }

    const valueText = typeof value === 'string' ? value.trim() : ''
    if (valueText && valueText !== '—') {
        return TACTICAL_TRIAD_SVOL_DEFAULT_STATE
    }

    return stateLabel
}

function normalizeCard(
    leg: TacticalTriadLeg,
    input: unknown,
    fallback: TacticalTriadCard
): TacticalTriadCard {
    if (!input || typeof input !== 'object') return fallback
    const raw = input as Partial<TacticalTriadCard>
    const subLabel = normalizeLabel(raw.sub_label ?? fallback.sub_label)
    const stateLabel = resolveStateLabel(
        leg,
        normalizeLabel(raw.state_label ?? fallback.state_label),
        subLabel,
        raw.value
    )
    const subIntensity = normalizeIntensity(raw.sub_intensity, fallback.sub_intensity)
    const tone = classifyTone(leg, stateLabel, subLabel)
    const theme = TACTICAL_TRIAD_CARD_THEME[tone]

    return {
        value: raw.value ?? fallback.value,
        state_label: stateLabel,
        color_class: theme.color_class,
        border_class: theme.border_class,
        bg_class: theme.bg_class,
        shadow_class: theme.shadow_class,
        animation: TACTICAL_TRIAD_PULSE_INTENSITIES.has(subIntensity) ? 'animate-pulse' : '',
        multiplier: raw.multiplier ?? fallback.multiplier ?? null,
        sub_intensity: subIntensity,
        sub_label: subLabel,
    }
}

export function normalizeTacticalTriadState(input: unknown): TacticalTriadState {
    if (!input || typeof input !== 'object') return TACTICAL_TRIAD_ZERO
    const raw = input as Partial<TacticalTriadState>
    return {
        vrp: normalizeCard('vrp', raw.vrp, TACTICAL_TRIAD_ZERO.vrp),
        charm: normalizeCard('charm', raw.charm, TACTICAL_TRIAD_ZERO.charm),
        svol: normalizeCard('svol', raw.svol, TACTICAL_TRIAD_ZERO.svol),
    }
}

import type { MtfFlowState, MtfTfState } from '../../types/dashboard'

export type FlowState = -1 | 0 | 1

export interface VisualTokenSet {
    dotColor: string
    textColor: string
    borderColor: string
    shadowClass: string
    animateClass: string
    barColor: string
    regimeLabel: string
}

export interface MtfTfViewState extends MtfTfState {
    tokens: VisualTokenSet
}

export interface MtfFlowViewState {
    m1: MtfTfViewState
    m5: MtfTfViewState
    m15: MtfTfViewState
    consensusState: FlowState
    consensusLabel: 'EXPANSION' | 'CONTRACTION' | 'EQUILIBRIUM'
    consensusPercent: number
    alignLabel: 'ALIGNED' | 'SPLIT' | 'DIVERGE'
    alignClass: string
}

const DEFAULT_TF: MtfTfState = {
    state: 0,
    relative_displacement: 0,
    pressure_gradient: 0,
    distance_to_vacuum: 0,
    kinetic_level: 0,
}

const DEFAULT_MTF_FLOW_STATE: MtfFlowState = {
    m1: { ...DEFAULT_TF },
    m5: { ...DEFAULT_TF },
    m15: { ...DEFAULT_TF },
}

export const STATE_THEME: Record<FlowState, VisualTokenSet> = {
    1: {
        dotColor: 'bg-accent-red',
        textColor: 'text-accent-red',
        borderColor: 'border-accent-red/30',
        shadowClass: 'shadow-[0_0_8px_rgba(255,77,79,0.5)]',
        animateClass: '',
        barColor: 'bg-accent-red',
        regimeLabel: 'EXP',
    },
    0: {
        dotColor: 'bg-zinc-700',
        textColor: 'text-text-secondary',
        borderColor: 'border-bg-border',
        shadowClass: 'shadow-none',
        animateClass: '',
        barColor: 'bg-zinc-600',
        regimeLabel: 'EQ',
    },
    [-1]: {
        dotColor: 'bg-accent-green',
        textColor: 'text-accent-green',
        borderColor: 'border-accent-green/30',
        shadowClass: 'shadow-[0_0_8px_rgba(0,214,143,0.5)]',
        animateClass: '',
        barColor: 'bg-accent-green',
        regimeLabel: 'CON',
    },
}

function toFiniteNumber(raw: unknown, fallback = 0): number {
    const value = typeof raw === 'number' ? raw : Number(raw)
    return Number.isFinite(value) ? value : fallback
}

function clamp01(value: number): number {
    if (value < 0) return 0
    if (value > 1) return 1
    return value
}

function normalizeFlowState(raw: unknown): FlowState {
    if (raw === 1 || raw === '1') return 1
    if (raw === -1 || raw === '-1') return -1
    if (raw === 0 || raw === '0') return 0
    return 0
}

function normalizeTfState(raw: unknown): MtfTfState {
    if (!raw || typeof raw !== 'object') return { ...DEFAULT_TF }
    const src = raw as Partial<MtfTfState>
    return {
        state: normalizeFlowState(src.state),
        relative_displacement: toFiniteNumber(src.relative_displacement, DEFAULT_TF.relative_displacement),
        pressure_gradient: toFiniteNumber(src.pressure_gradient, DEFAULT_TF.pressure_gradient),
        distance_to_vacuum: Math.max(0, toFiniteNumber(src.distance_to_vacuum, DEFAULT_TF.distance_to_vacuum)),
        kinetic_level: clamp01(toFiniteNumber(src.kinetic_level, DEFAULT_TF.kinetic_level)),
    }
}

function toViewState(tf: MtfTfState): MtfTfViewState {
    const tokens = STATE_THEME[tf.state]
    const animateClass = tf.kinetic_level >= 0.85 ? 'animate-pulse' : tokens.animateClass
    return {
        ...tf,
        tokens: {
            ...tokens,
            animateClass,
        },
    }
}

function deriveConsensus(states: FlowState[]): FlowState {
    const balance = states.reduce((acc, value) => acc + value, 0 as number)
    if (balance > 0) return 1
    if (balance < 0) return -1
    return 0
}

function deriveAlignmentLabel(states: FlowState[]): 'ALIGNED' | 'SPLIT' | 'DIVERGE' {
    const total = states.length || 1
    const dominantCount = Math.max(
        states.filter((s) => s === 1).length,
        states.filter((s) => s === -1).length,
        states.filter((s) => s === 0).length
    )
    const alignment = dominantCount / total
    if (alignment >= 0.67) return 'ALIGNED'
    if (alignment >= 0.34) return 'SPLIT'
    return 'DIVERGE'
}

function alignClassFrom(label: 'ALIGNED' | 'SPLIT' | 'DIVERGE', consensus: FlowState): string {
    if (label === 'ALIGNED') {
        return STATE_THEME[consensus].textColor
    }
    if (label === 'SPLIT') return 'text-accent-amber'
    return 'text-text-secondary'
}

function consensusLabelFrom(state: FlowState): 'EXPANSION' | 'CONTRACTION' | 'EQUILIBRIUM' {
    if (state > 0) return 'EXPANSION'
    if (state < 0) return 'CONTRACTION'
    return 'EQUILIBRIUM'
}

export function normalizeMtfFlowState(input: unknown): MtfFlowViewState {
    if (!input || typeof input !== 'object') {
        const m1 = toViewState(DEFAULT_MTF_FLOW_STATE.m1)
        const m5 = toViewState(DEFAULT_MTF_FLOW_STATE.m5)
        const m15 = toViewState(DEFAULT_MTF_FLOW_STATE.m15)
        return {
            m1,
            m5,
            m15,
            consensusState: 0,
            consensusLabel: 'EQUILIBRIUM',
            consensusPercent: 0,
            alignLabel: 'DIVERGE',
            alignClass: 'text-text-secondary',
        }
    }

    const src = input as Partial<MtfFlowState>
    const m1 = toViewState(normalizeTfState(src.m1))
    const m5 = toViewState(normalizeTfState(src.m5))
    const m15 = toViewState(normalizeTfState(src.m15))
    const states: FlowState[] = [m1.state, m5.state, m15.state]
    const consensusState = deriveConsensus(states)
    const alignLabel = deriveAlignmentLabel(states)
    const consensusPercent = Math.round(((m1.kinetic_level + m5.kinetic_level + m15.kinetic_level) / 3) * 100)

    return {
        m1,
        m5,
        m15,
        consensusState,
        consensusLabel: consensusLabelFrom(consensusState),
        consensusPercent,
        alignLabel,
        alignClass: alignClassFrom(alignLabel, consensusState),
    }
}

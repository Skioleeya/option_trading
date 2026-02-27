// Types for all WebSocket dashboard data

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'

export type GexRegime = 'SUPER_PIN' | 'DAMPING' | 'NEUTRAL' | 'ACCELERATION'
export type IVVelocityState = 'PAID_MOVE' | 'ORGANIC_GRIND' | 'HOLLOW_RISE' | 'HOLLOW_DROP' | 'PAID_DROP' | 'VOL_EXPANSION' | 'EXHAUSTION' | 'UNAVAILABLE'
export type VannaFlowState = 'DANGER_ZONE' | 'GRIND_STABLE' | 'NORMAL' | 'VANNA_FLIP' | 'UNAVAILABLE'

export interface FusedSignal {
    direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
    confidence: number
    weights: { iv: number; wall: number; vanna: number; mtf: number }
    regime: string
    iv_regime: string
    gex_intensity: string
    explanation: string
    components: Record<string, { direction: string; confidence: number; weight: number }>
}

export interface IVVelocityResult {
    state: IVVelocityState
    confidence: number
    iv_roc: number | null
    spot_roc: number | null
}

export interface VannaFlowResult {
    state: VannaFlowState
    correlation: number | null
    gex_regime: GexRegime
    net_gex: number | null
    confidence: number
    iv_roc: number | null
    iv_acceleration: number | null
}

export interface WallMigrationResult {
    call_wall_state: string
    put_wall_state: string
    confidence: number
    call_wall_delta: number | null
    put_wall_delta: number | null
}

export interface MicroStructureState {
    iv_velocity: IVVelocityResult | null
    wall_migration: WallMigrationResult | null
    vanna_flow_result: VannaFlowResult | null
}

export interface GammaWalls {
    call_wall: number | null
    put_wall: number | null
}

export interface PerStrikeGex {
    strike: number
    call_gex: number
    put_gex: number
    net_gex: number
}

export interface ActiveOption {
    symbol: string
    option_type: 'CALL' | 'PUT'
    strike: number
    implied_volatility: number
    volume: number
    turnover: number
    flow: number
}

export interface AgentBData {
    net_gex: number | null
    spy_atm_iv: number | null
    gamma_walls: GammaWalls
    gamma_flip: boolean
    gamma_flip_level: number | null
    per_strike_gex: PerStrikeGex[]
    micro_structure: { micro_structure_state: MicroStructureState } | null
    iv_confidence: number
    wall_confidence: number
    vanna_confidence: number
    mtf_consensus: { consensus: string; strength: number; timeframes: Record<string, string> }
}

export interface AgentAData {
    spot: number | null
    vwap: number | null
    vwap_std: number
    slope: number
}

export interface AgentGResult {
    agent: 'agent_g'
    signal: string
    as_of: string
    data: {
        agent_a: { signal: string; data: AgentAData }
        agent_b: { signal: string; data: AgentBData }
        net_gex: number | null
        gex_regime: GexRegime
        gamma_walls: GammaWalls
        gamma_flip_level: number | null
        trap_state: string
        fused_signal: FusedSignal
        micro_structure: { micro_structure_state: MicroStructureState } | null
    }
}

export interface DashboardPayload {
    type: 'dashboard_update' | 'dashboard_init' | 'keepalive'
    timestamp: string
    spot: number | null
    agent_g: AgentGResult | null
}

// ATM Decay
export interface AtmDecay {
    atm_strike: number | null
    straddle_pct: number | null
    call_pct: number | null
    put_pct: number | null
}

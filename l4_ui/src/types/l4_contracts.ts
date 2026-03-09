/**
 * l4_ui — L4 Type Contracts (Phase 2)
 * ──────────────────────────────────────────
 * TypeScript types mirroring the L3 FrozenPayload / UIState Python
 * frozen-dataclass hierarchy from `l3_assembly/events/payload_events.py`.
 *
 * Goal: replace `const uiState: any` in App.tsx with `L4UIState`,
 *       making type errors surface at compile time instead of runtime.
 *
 * Naming convention:
 *   L4MetricCard   ↔  MetricCard     (payload_events.py)
 *   L4UIState      ↔  UIState        (payload_events.py)
 *   L4FrozenPayload ↔ FrozenPayload  (payload_events.py)
 */
import type {
    ActiveOption,
    MtfFlowState,
    SkewDynamicsState,
    TacticalTriadState,
} from './dashboard'

// ─────────────────────────────────────────────────────────────────────────────
// Atomic types
// ─────────────────────────────────────────────────────────────────────────────

/** Badge token whitelist matching MetricCard.__post_init__ validation. */
export type BadgeToken =
    | 'badge-neutral'
    | 'badge-amber'
    | 'badge-red'
    | 'badge-green'
    | 'badge-purple'
    | 'badge-cyan'
    | 'badge-hollow-purple'
    | 'badge-hollow-amber'
    | 'badge-hollow-cyan'
    | 'badge-hollow-green'
    | 'badge-red-dim'

/**
 * Mirrors L3 MetricCard frozen dataclass.
 * frontend legacy schema: { label: string, badge: string }
 */
export interface L4MetricCard {
    label: string
    badge: BadgeToken
    tooltip?: string
}

// ─────────────────────────────────────────────────────────────────────────────
// MicroStats
// ─────────────────────────────────────────────────────────────────────────────

/** Mirrors L3 MicroStatsState. */
export interface L4MicroStats {
    net_gex: L4MetricCard
    wall_dyn: L4MetricCard
    vanna: L4MetricCard
    momentum: L4MetricCard
}

// ─────────────────────────────────────────────────────────────────────────────
// WallMigration
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Mirrors WallMigrationRow.to_dict() output.
 * Kept intentionally close to the existing frontend types/dashboard.ts
 * shape for zero component prop change.
 */
export interface L4WallMigrationRow {
    label: string
    strike: number | null
    state: string
    history: number[]
    lights: Record<string, string>
}

// ─────────────────────────────────────────────────────────────────────────────
// DepthProfile
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Mirrors DepthProfileRow.to_dict() output.
 * Contains the full render-hint set used by the Canvas/SVG renderer.
 */
export interface L4DepthProfileRow {
    strike: number
    put_pct: number
    call_pct: number
    put_color: string
    call_color: string
    put_label_color: string
    call_label_color: string
    spot_tag_classes: string
    flip_tag_classes: string
    is_dominant_put: boolean
    is_dominant_call: boolean
    is_spot: boolean
    is_flip: boolean
    strike_color: string
}

// ─────────────────────────────────────────────────────────────────────────────
// ATM Decay
// ─────────────────────────────────────────────────────────────────────────────

/** Mirrors AtmDecay from types/dashboard.ts (already well-typed). */
export interface L4AtmDecay {
    strike: number | null
    locked_at: string | null
    straddle_pct: number | null
    call_pct: number | null
    put_pct: number | null
    timestamp?: string
}

// ─────────────────────────────────────────────────────────────────────────────
// UIState (top-level container)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Mirrors UIState from payload_events.py.
 * All optional fields use null (not undefined) to match Python's to_dict().
 */
export interface L4UIState {
    micro_stats: L4MicroStats
    wall_migration: L4WallMigrationRow[]
    depth_profile: L4DepthProfileRow[]
    macro_volume_map: Record<string, number>
    atm: L4AtmDecay | null

    tactical_triad: TacticalTriadState | null
    skew_dynamics: SkewDynamicsState | null
    active_options: ActiveOption[] | null
    mtf_flow: MtfFlowState | null
}

// ─────────────────────────────────────────────────────────────────────────────
// FrozenPayload (full broadcast unit from L3)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Mirrors FrozenPayload.to_dict() from payload_events.py.
 * This is the root type that the backend broadcasts every 1 Hz.
 *
 * Note: kept backward-compatible with DashboardPayload from types/dashboard.ts
 *       so existing components can be gradually migrated.
 */
export interface L4FrozenPayload {
    /** Monotonic broadcast version (from FieldDeltaEncoder). */
    version: number
    /** Legacy payload timestamp field; canonical value is UTC ISO8601 from L0 source data time. */
    as_of: string
    spot: number | null
    ui_state: L4UIState
    /** Direction: BULLISH | BEARISH | NEUTRAL | HALT */
    signal: string
    /** Confidence score 0.0–1.0 */
    confidence: number
}

// ─────────────────────────────────────────────────────────────────────────────
// Type Guards
// ─────────────────────────────────────────────────────────────────────────────

/** Runtime guard: does the object look like a valid L4 payload? */
export function isValidL4Payload(data: unknown): data is L4FrozenPayload {
    if (typeof data !== 'object' || data === null) return false
    const d = data as Record<string, unknown>
    return (
        typeof d['as_of'] === 'string' &&
        typeof d['ui_state'] === 'object' &&
        d['ui_state'] !== null
    )
}

/** Runtime guard: does this look like a valid MetricCard? */
export function isMetricCard(val: unknown): val is L4MetricCard {
    if (typeof val !== 'object' || val === null) return false
    const v = val as Record<string, unknown>
    return typeof v['label'] === 'string' && typeof v['badge'] === 'string'
}

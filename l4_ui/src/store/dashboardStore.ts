/**
 * l4_ui — DashboardStore (Phase 1: State Decoupling)
 * ─────────────────────────────────────────────────────────
 * Zustand store with subscribeWithSelector middleware.
 *
 * Replaces scattered useState in useDashboardWS.ts with a single
 * immutable state tree. Each UI component subscribes only to its own
 * slice, eliminating full-tree re-renders on every WS message.
 *
 * Architecture:
 *   ProtocolAdapter → DeltaDecoder → dashboardStore → Component Selectors
 *
 * Backwards compatibility:
 *   useDashboardWS() continues to export { status, payload, sendPing }.
 *   All existing App.tsx / component code unchanged.
 */

import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import type {
    DashboardPayload,
    ConnectionStatus,
    AtmDecay,
} from '../types/dashboard'

// ─────────────────────────────────────────────────────────────────────────────
// State Shape
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Top-level dashboard state.
 *
 * Derived slices (spot, atm, uiState) are flattened here so that
 * components can subscribe with minimal selector depth and maximum
 * selector precision.
 */
export interface DashboardState {
    // ── Connection ──────────────────────────────────────────────────────────
    /** 3-state; extended to 5-state by connectionMonitor in Phase 2. */
    connectionStatus: ConnectionStatus

    // ── Raw payload (full, for backward compat) ─────────────────────────────
    /** The full last-seen payload. Used by useDashboardWS shim. */
    payload: DashboardPayload | null

    // ── Field-level slices (for component selectors) ─────────────────────────
    spot: number | null
    ivPct: number | null
    /** Monotonic version counter; incremented on every state write. */
    version: number

    // ── ATM Decay series ────────────────────────────────────────────────────
    /** Latest ATM tick (mutable reference to last payload atm). */
    atm: AtmDecay | null
    /** Append-only ring buffer, max 500 ticks. Kept for AtmDecayChart. */
    atmHistory: AtmDecay[]

    // ── Actions ─────────────────────────────────────────────────────────────
    setConnectionStatus: (status: ConnectionStatus) => void

    /**
     * Full update: replace entire payload, re-extract slices.
     * Called when server sends 'dashboard_update' / 'dashboard_init'.
     */
    applyFullUpdate: (payload: DashboardPayload) => void

    /** Delta update: merge a JSON-Patch result on top of current payload. */
    applyMergedPayload: (next: DashboardPayload) => void

    /** Push a new ATM tick into history (de-duplicates by timestamp). */
    appendAtmHistory: (tick: AtmDecay) => void

    /** Hydrate history from API (merges with existing live ticks). */
    hydrateAtmHistory: (history: AtmDecay[]) => void
}
// ─────────────────────────────────────────────────────────────────────────────
// Sticky-key protection Constants
// ─────────────────────────────────────────────────────────────────────────────

/**
 * ui_state keys that should NEVER be blanked by a transient empty update.
 * Mirrors the STICKY_KEYS set in the original useDashboardWS.ts.
 */
const STICKY_KEYS = [
    'wall_migration',
    'depth_profile',
    'active_options',
    'tactical_triad',
    'skew_dynamics',
    'macro_volume_map',
] as const

type StickyKey = (typeof STICKY_KEYS)[number]

/** Returns true if value is considered "empty" for sticky-key purposes. */
function isEmpty(val: unknown): boolean {
    if (val === null || val === undefined) return true
    if (Array.isArray(val)) return val.length === 0
    if (typeof val === 'object') return Object.keys(val as object).length === 0
    return false
}

/**
 * Merge next ui_state on top of prev ui_state.
 * Sticky keys: if new value is empty but old had data, keep old.
 *
 * Logic 100% equivalent to the original smartMergeUiState() in
 * useDashboardWS.ts — extracted here so it can be unit-tested.
 */
export function smartMergeUiState(prev: any, next: any): any {
    const merged = { ...prev, ...next }
    for (const key of STICKY_KEYS as readonly StickyKey[]) {
        const newVal = next?.[key]
        const oldVal = prev?.[key]
        if (isEmpty(newVal) && !isEmpty(oldVal)) {
            merged[key] = oldVal
        }
    }
    return merged
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

const MAX_ATM_HISTORY = 5000 // Reduced from 50000 to improve rendering performance

function extractSpot(p: DashboardPayload): number | null {
    return p?.spot ?? null
}

function extractIvPct(p: DashboardPayload): number | null {
    return p?.agent_g?.data?.spy_atm_iv ?? null
}

function extractAtm(p: DashboardPayload): AtmDecay | null {
    // FrozenPayload.to_dict() places atm at the payload root (payload.atm),
    // NOT inside agent_g.data.ui_state. UIState.to_dict() emits no 'atm' key.
    // Fallback to ui_state.atm kept for forward-compat if schema is ever mirrored.
    return p?.atm ?? p?.agent_g?.data?.ui_state?.atm ?? null
}

/**
 * Build the next merged full-payload from (prev, next), applying smart
 * ui_state merge so sticky keys are never erased.
 */
function mergePayloads(
    prev: DashboardPayload | null,
    next: DashboardPayload
): DashboardPayload {
    if (!prev) return next
    const prevUiState = prev.agent_g?.data?.ui_state ?? {}
    const nextUiState = next.agent_g?.data?.ui_state ?? {}
    const mergedUiState = smartMergeUiState(prevUiState, nextUiState)
    return {
        ...prev,
        ...next,
        agent_g: next.agent_g
            ? {
                ...next.agent_g,
                data: {
                    ...(next.agent_g.data ?? {}),
                    ui_state: mergedUiState,
                },
            }
            : prev.agent_g,
    } as DashboardPayload
}

// ─────────────────────────────────────────────────────────────────────────────
// Store
// ─────────────────────────────────────────────────────────────────────────────

export const useDashboardStore = create<DashboardState>()(
    subscribeWithSelector((set, get) => ({
        // ── Initial State ──────────────────────────────────────────────────────
        connectionStatus: 'connecting',
        payload: null,
        spot: null,
        ivPct: null,
        atm: null,
        atmHistory: [],
        version: 0,

        // ── Actions ────────────────────────────────────────────────────────────

        setConnectionStatus: (status) => set({ connectionStatus: status }),

        applyFullUpdate: (incoming) => {
            const prev = get().payload
            const merged = mergePayloads(prev, incoming)
            const atm = extractAtm(merged)

            if (atm === null && get().atm !== null) {
                console.warn('[L4 Debug] ATM becoming NULL in applyFullUpdate. Prev:', get().atm, 'Incoming:', incoming);
            }

            set((state) => {
                let nextHistory = state.atmHistory
                if (atm && !state.atmHistory.some((t) => t.timestamp === atm.timestamp)) {
                    const last = state.atmHistory[state.atmHistory.length - 1]
                    const isStatic = last &&
                        Math.abs((last.call_pct || 0) - (atm.call_pct || 0)) < 1e-6 &&
                        Math.abs((last.put_pct || 0) - (atm.put_pct || 0)) < 1e-6 &&
                        Math.abs((last.straddle_pct || 0) - (atm.straddle_pct || 0)) < 1e-6

                    if (isStatic) {
                        nextHistory = [...state.atmHistory.slice(0, -1), atm]
                    } else {
                        nextHistory = [...state.atmHistory.slice(-MAX_ATM_HISTORY + 1), atm]
                    }
                }

                return {
                    payload: merged,
                    spot: extractSpot(merged),
                    ivPct: extractIvPct(merged),
                    atm,
                    atmHistory: nextHistory,
                    version: state.version + 1,
                }
            })
        },

        applyMergedPayload: (next) => {
            // DeltaDecoder has already applied JSON-Patch; we still run the
            // ui_state sticky-merge here for belt-and-suspenders safety.
            const prev = get().payload
            const merged = mergePayloads(prev, next)
            const atm = extractAtm(merged)

            if (atm === null && get().atm !== null) {
                console.warn('[L4 Debug] ATM becoming NULL in applyMergedPayload. Prev:', get().atm, 'Incoming:', next);
            }

            set((state) => {
                let nextHistory = state.atmHistory
                if (atm && !state.atmHistory.some((t) => t.timestamp === atm.timestamp)) {
                    const last = state.atmHistory[state.atmHistory.length - 1]
                    const isStatic = last &&
                        Math.abs((last.call_pct || 0) - (atm.call_pct || 0)) < 1e-6 &&
                        Math.abs((last.put_pct || 0) - (atm.put_pct || 0)) < 1e-6 &&
                        Math.abs((last.straddle_pct || 0) - (atm.straddle_pct || 0)) < 1e-6

                    if (isStatic) {
                        nextHistory = [...state.atmHistory.slice(0, -1), atm]
                    } else {
                        nextHistory = [...state.atmHistory.slice(-MAX_ATM_HISTORY + 1), atm]
                    }
                }

                return {
                    payload: merged,
                    spot: extractSpot(merged),
                    ivPct: extractIvPct(merged),
                    atm,
                    atmHistory: nextHistory,
                    version: state.version + 1,
                }
            })
        },

        appendAtmHistory: (tick) => {
            set((state) => {
                if (state.atmHistory.some((t) => t.timestamp === tick.timestamp)) {
                    return state // de-dup
                }
                return {
                    atmHistory: [...state.atmHistory.slice(-MAX_ATM_HISTORY + 1), tick],
                }
            })
        },

        hydrateAtmHistory: (history) => {
            set((state) => {
                const existingTimestamps = new Set(state.atmHistory.map((t) => t.timestamp))
                const newPoints = history.filter((t) => t.timestamp && !existingTimestamps.has(t.timestamp))

                if (newPoints.length === 0) return state

                const combined = [...state.atmHistory, ...newPoints].sort((a, b) =>
                    (a.timestamp || '').localeCompare(b.timestamp || '')
                )

                return {
                    atmHistory: combined.slice(-MAX_ATM_HISTORY),
                }
            })
        },
    }))
)

// ─────────────────────────────────────────────────────────────────────────────
// Named selectors — import directly in components for precise subscription
// ─────────────────────────────────────────────────────────────────────────────

/** Selector: full payload (for backward-compat App.tsx shim) */
export const selectPayload = (s: DashboardState) => s.payload

/** Selector: connection status */
export const selectConnectionStatus = (s: DashboardState) =>
    s.connectionStatus

/** Selector: spot price */
export const selectSpot = (s: DashboardState) => s.spot

/** Selector: iv% */
export const selectIvPct = (s: DashboardState) => s.ivPct

/** Selector: ATM decay (latest tick) */
export const selectAtm = (s: DashboardState) => s.atm

/** Selector: ATM history (chart data) */
export const selectAtmHistory = (s: DashboardState) => s.atmHistory

/** Selector: ui_state sub-tree */
export const selectUiState = (s: DashboardState) =>
    s.payload?.agent_g?.data?.ui_state ?? null

/** Selector: fused signal */
export const selectFused = (s: DashboardState) =>
    s.payload?.agent_g?.data?.fused_signal ?? null

/** Selector: net_gex */
export const selectNetGex = (s: DashboardState) =>
    s.payload?.agent_g?.data?.net_gex ?? null

/** Selector: gamma walls */
export const selectGammaWalls = (s: DashboardState) =>
    s.payload?.agent_g?.data?.gamma_walls ?? null

/** Selector: gamma flip level */
export const selectFlipLevel = (s: DashboardState) =>
    s.payload?.agent_g?.data?.gamma_flip_level ?? null

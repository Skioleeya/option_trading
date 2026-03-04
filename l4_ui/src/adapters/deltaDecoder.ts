/**
 * l4_ui — DeltaDecoder (Phase 1: Protocol & State Decoupling)
 * ──────────────────────────────────────────────────────────────────
 * Isolated, side-effect-free JSON-Patch decoder.
 *
 * Extracted from the original useDashboardWS.ts onmessage handler.
 * All logic is preserved bit-for-bit; this module is now independently
 * unit-testable.
 *
 * Usage:
 *   const result = DeltaDecoder.applyPatch(prev, data.patch)
 *   // OR
 *   const result = DeltaDecoder.applyChanges(prev, data.changes)
 *   if (result.ok) store.applyMergedPayload(result.value)
 */

import { applyPatch } from 'fast-json-patch'
import type { DashboardPayload } from '../types/dashboard'

// ─────────────────────────────────────────────────────────────────────────────
// Result type
// ─────────────────────────────────────────────────────────────────────────────

export type DecodeResult<T> =
    | { ok: true; value: T }
    | { ok: false; error: unknown }

// ─────────────────────────────────────────────────────────────────────────────
// DeltaDecoder
// ─────────────────────────────────────────────────────────────────────────────

export const DeltaDecoder = {
    /**
     * Apply a JSON-Patch operation set to a previous dashboard payload.
     *
     * ⚠ PP-PATCH FIX (preserved from original):
     *   `mutateDocument=false` often causes aliasing and duplicating
     *   elements in React arrays.  We serialize/deserialize to deep clone,
     *   then apply the patch mutably for robust array transformations.
     *
     * @param prev    - Current store state (cloned internally, not mutated)
     * @param patch   - RFC 6902 JSON-Patch operations array
     * @param meta    - Optional heartbeat/timestamp metadata from the delta frame
     * @returns       - DecodeResult<DashboardPayload>
     */
    applyPatch(
        prev: DashboardPayload,
        patch: unknown[],
        meta?: { heartbeat_timestamp?: string; timestamp?: string }
    ): DecodeResult<DashboardPayload> {
        try {
            // Deep-clone to avoid aliasing in React state (original comment preserved)
            const prevClone: DashboardPayload = JSON.parse(JSON.stringify(prev))
            const result = applyPatch(prevClone, patch as any, false, true)

            const next = result.newDocument as DashboardPayload

            // Inject heartbeat/timestamp from the delta envelope if present
            const withMeta: DashboardPayload = {
                ...next,
                ...(meta?.heartbeat_timestamp !== undefined
                    ? { heartbeat_timestamp: meta.heartbeat_timestamp }
                    : {}),
                ...(meta?.timestamp !== undefined ? { timestamp: meta.timestamp } : {}),
            }

            return { ok: true, value: withMeta }
        } catch (error) {
            return { ok: false, error }
        }
    },

    /**
     * Apply a field-level changes dictionary (Backend preferred format).
     * Maps flat keys like 'agent_g_ui_state' to nested store paths.
     */
    applyChanges(
        prev: DashboardPayload,
        changes: Record<string, any>,
        meta?: { heartbeat_timestamp?: string; timestamp?: string }
    ): DecodeResult<DashboardPayload> {
        try {
            // Deep clone to avoid mutation
            const next: DashboardPayload = JSON.parse(JSON.stringify(prev))

            // 1. Scalar top-level fields
            const topLevel = ["spot", "drift_ms", "drift_warning", "is_stale", "version", "data_timestamp", "heartbeat_timestamp"]
            for (const key of topLevel) {
                if (changes[key] !== undefined) {
                    (next as any)[key] = changes[key]
                }
            }

            // 2. Signal (maps to agent_g.data)
            if (changes.signal && next.agent_g?.data) {
                next.agent_g.data = {
                    ...next.agent_g.data,
                    ...changes.signal
                }
            }

            // 3. UI State (maps to agent_g.data.ui_state)
            if (changes.agent_g_ui_state && next.agent_g?.data?.ui_state) {
                next.agent_g.data.ui_state = {
                    ...next.agent_g.data.ui_state,
                    ...changes.agent_g_ui_state
                }
            }

            // 4. ATM
            if (changes.atm !== undefined) {
                next.atm = changes.atm
            }

            // 5. Inject meta
            if (meta?.heartbeat_timestamp) next.heartbeat_timestamp = meta.heartbeat_timestamp
            if (meta?.timestamp) next.timestamp = meta.timestamp
            if (changes.heartbeat_timestamp) next.heartbeat_timestamp = changes.heartbeat_timestamp

            return { ok: true, value: next }
        } catch (error) {
            return { ok: false, error }
        }
    },

    /**
     * Parse a raw WebSocket message string.
     * Returns the parsed object or null if JSON is invalid.
     */
    parseMessage(raw: string): unknown | null {
        try {
            return JSON.parse(raw)
        } catch {
            return null
        }
    },

    /**
     * Type predicate: is this a keepalive frame?
     */
    isKeepalive(msg: unknown): boolean {
        return (
            msg !== null &&
            typeof msg === 'object' &&
            (msg as any).type === 'keepalive'
        )
    },

    /**
     * Type predicate: is this a delta frame?
     */
    isDelta(msg: unknown): boolean {
        return (
            msg !== null &&
            typeof msg === 'object' &&
            (msg as any).type === 'dashboard_delta'
        )
    },
} as const

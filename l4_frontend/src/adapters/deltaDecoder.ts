/**
 * l4_frontend — DeltaDecoder (Phase 1: Protocol & State Decoupling)
 * ──────────────────────────────────────────────────────────────────
 * Isolated, side-effect-free JSON-Patch decoder.
 *
 * Extracted from the original useDashboardWS.ts onmessage handler.
 * All logic is preserved bit-for-bit; this module is now independently
 * unit-testable.
 *
 * Usage:
 *   const result = DeltaDecoder.applyPatch(prev, data.patch)
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

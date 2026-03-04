/**
 * l4_ui — useDashboardWS (Phase 1: Thin Wrapper)
 * ──────────────────────────────────────────────────────
 * This hook is now a thin integration layer.
 *
 * Original behaviour (100% preserved):
 *   Returns { status, payload, sendPing }
 *   All consumers (App.tsx, components) continue working unchanged.
 *
 * What changed internally:
 *   • WebSocket management → ProtocolAdapter
 *   • Delta-patch logic    → DeltaDecoder
 *   • State management     → DashboardStore (Zustand)
 *   • This hook: only mounts/unmounts adapter + reads from store
 */

import { useEffect, useRef } from 'react'
import { ProtocolAdapter } from '../adapters/protocolAdapter'
import {
    useDashboardStore,
    selectPayload,
    selectConnectionStatus,
} from '../store/dashboardStore'

// ─────────────────────────────────────────────────────────────────────────────
// Config (kept identical to original for easy comparison)
// ─────────────────────────────────────────────────────────────────────────────

const WS_URL = 'ws://localhost:8001/ws/dashboard'
const RECONNECT_DELAY_MS = 2000
const MAX_RECONNECT_DELAY_MS = 30_000

// ─────────────────────────────────────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────────────────────────────────────

export function useDashboardWS() {
    // Read from Zustand store with field-level selectors
    const status = useDashboardStore(selectConnectionStatus)
    const payload = useDashboardStore(selectPayload)

    // Stable ref to the adapter instance (not re-created on re-render)
    const adapterRef = useRef<ProtocolAdapter | null>(null)

    useEffect(() => {
        // Extract only the store actions we hand to the adapter
        const {
            setConnectionStatus,
            applyFullUpdate,
            applyMergedPayload,
        } = useDashboardStore.getState()

        const adapter = new ProtocolAdapter({
            url: WS_URL,
            store: { setConnectionStatus, applyFullUpdate, applyMergedPayload },
            initialReconnectDelayMs: RECONNECT_DELAY_MS,
            maxReconnectDelayMs: MAX_RECONNECT_DELAY_MS,
        })

        // Wire up the payload getter so the adapter can read current state
        // when applying delta patches (avoids circular import of the store)
        adapter.setPayloadGetter(() => useDashboardStore.getState().payload)

        adapterRef.current = adapter
        adapter.connect()

        return () => {
            adapter.disconnect()
            adapterRef.current = null
        }
    }, []) // mount once

    const sendPing = () => adapterRef.current?.sendPing()

    return { status, payload, sendPing }
}

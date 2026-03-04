import { useEffect, useRef, useState, useCallback } from 'react'
import { applyPatch } from 'fast-json-patch'
import type { ConnectionStatus, DashboardPayload } from '../types/dashboard'

const WS_URL = 'ws://localhost:8001/ws/dashboard'
const RECONNECT_DELAY_MS = 2000
const MAX_RECONNECT_DELAY_MS = 30000

// Fields that should never be blanked by a transient empty update.
// If new data provides an empty array / null for these keys but prior
// state had real data, we keep the prior data.
const STICKY_KEYS = ['wall_migration', 'depth_profile', 'active_options', 'tactical_triad', 'skew_dynamics', 'macro_volume_map'] as const

function smartMergeUiState(prev: any, next: any): any {
    const merged = { ...prev, ...next }
    for (const key of STICKY_KEYS) {
        const newVal = next[key]
        const oldVal = prev[key]
        const newIsEmpty = newVal === null || newVal === undefined ||
            (Array.isArray(newVal) && newVal.length === 0) ||
            (typeof newVal === 'object' && !Array.isArray(newVal) && Object.keys(newVal).length === 0)
        const oldHasData = oldVal !== null && oldVal !== undefined &&
            (!Array.isArray(oldVal) || oldVal.length > 0) &&
            (Array.isArray(oldVal) || Object.keys(oldVal).length > 0)
        if (newIsEmpty && oldHasData) {
            merged[key] = oldVal
        }
    }
    return merged
}

export function useDashboardWS() {
    const [status, setStatus] = useState<ConnectionStatus>('connecting')
    const [payload, setPayload] = useState<DashboardPayload | null>(null)
    const wsRef = useRef<WebSocket | null>(null)
    const reconnectDelay = useRef(RECONNECT_DELAY_MS)
    const mountedRef = useRef(true)

    const connect = useCallback(() => {
        if (!mountedRef.current) return
        setStatus('connecting')

        const ws = new WebSocket(WS_URL)
        wsRef.current = ws

        ws.onopen = () => {
            if (!mountedRef.current) return
            console.info("[L4 WS] Connected to backend.");
            setStatus('connected')
            reconnectDelay.current = RECONNECT_DELAY_MS
        }

        ws.onmessage = (evt) => {
            if (!mountedRef.current) return
            try {
                const data: any = JSON.parse(evt.data)
                if (data.type === 'keepalive') return

                if (data.type === 'dashboard_delta') {
                    setPayload(prev => {
                        if (!prev) return prev;
                        try {
                            // PP-PATCH FIX: 'mutateDocument=false' often causes aliasing and duplicating
                            // elements in React arrays. We serialize/deserialize to deep clone,
                            // then apply the patch mutably for robust array transformations.
                            const prevClone = JSON.parse(JSON.stringify(prev));
                            const result = applyPatch(prevClone, data.patch, false, true);
                            return {
                                ...(result.newDocument as DashboardPayload),
                                heartbeat_timestamp: data.heartbeat_timestamp,
                                timestamp: data.timestamp
                            };
                        } catch (e) {
                            console.error(`[L4 WS] Failed to apply JSON patch:`, e, "Patch Payload:", data.patch);
                            return prev;
                        }
                    });
                    return;
                }

                // Merge instead of replace: preserve existing ui_state fields when
                // a frame is incomplete (e.g. during agent early-returns or errors).
                // Smart merge: sticky fields never get overwritten with empty data.
                setPayload(prev => {
                    if (!prev) return data
                    const prevUiState = prev.agent_g?.data?.ui_state ?? {}
                    const newUiState = data.agent_g?.data?.ui_state ?? {}
                    const mergedUiState = smartMergeUiState(prevUiState, newUiState)
                    return {
                        ...prev,
                        ...data,
                        agent_g: data.agent_g ? {
                            ...data.agent_g,
                            data: {
                                ...((data.agent_g.data ?? {}) as object),
                                ui_state: mergedUiState,
                            }
                        } : prev.agent_g,
                    } as DashboardPayload
                })
            } catch {
                // ignore parse errors
            }
        }

        ws.onclose = () => {
            if (!mountedRef.current) return
            setStatus('disconnected')
            // Exponential backoff reconnect
            const delay = reconnectDelay.current
            console.warn("[L4 WS] Disconnected. Reconnecting in", delay, "ms");
            reconnectDelay.current = Math.min(delay * 1.5, MAX_RECONNECT_DELAY_MS)
            setTimeout(connect, delay)
        }

        ws.onerror = () => {
            ws.close()
        }
    }, [])

    useEffect(() => {
        mountedRef.current = true
        connect()
        return () => {
            mountedRef.current = false
            wsRef.current?.close()
        }
    }, [connect])

    const sendPing = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send('ping')
        }
    }, [])

    return { status, payload, sendPing }
}

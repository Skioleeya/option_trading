import { useEffect, useRef, useState, useCallback } from 'react'
import { applyPatch } from 'fast-json-patch'
import type { ConnectionStatus, DashboardPayload } from '../types/dashboard'

const WS_URL = 'ws://localhost:8001/ws/dashboard'
const RECONNECT_DELAY_MS = 2000
const MAX_RECONNECT_DELAY_MS = 30000

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
                            const result = applyPatch(prev, data.patch, false, false);
                            return {
                                ...(result.newDocument as DashboardPayload),
                                heartbeat_timestamp: data.heartbeat_timestamp,
                                timestamp: data.timestamp
                            };
                        } catch (e) {
                            console.error("Failed to apply JSON patch", e);
                            return prev;
                        }
                    });
                    return;
                }

                // Merge instead of replace: preserve existing ui_state fields when
                // a frame is incomplete (e.g. during agent early-returns or errors).
                setPayload(prev => {
                    if (!prev) return data
                    const prevUiState = prev.agent_g?.data?.ui_state ?? {}
                    const newUiState = data.agent_g?.data?.ui_state ?? {}
                    const mergedUiState = { ...prevUiState, ...newUiState }
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

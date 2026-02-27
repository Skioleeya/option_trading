import { useEffect, useRef, useState, useCallback } from 'react'
import type { ConnectionStatus, DashboardPayload } from '../types/dashboard'

const WS_URL = 'ws://localhost:8000/ws/dashboard'
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
                const data: DashboardPayload = JSON.parse(evt.data)
                if (data.type === 'keepalive') return
                setPayload(data)
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

/**
 * useDashboardWS — side-effect-only websocket bootstrap.
 *
 * This hook intentionally does not subscribe React to hot store state.
 * The websocket adapter writes directly into Zustand and components read
 * the slices they need through selectors.
 */
import { useEffect, useRef } from 'react'
import { ProtocolAdapter } from '../adapters/protocolAdapter'
import { useDashboardStore } from '../store/dashboardStore'
import { ConnectionMonitor } from '../observability/connectionMonitor'
import { runtimeConfig } from '../config/runtime'

const RECONNECT_DELAY_MS = 2000
const MAX_RECONNECT_DELAY_MS = 30_000

export function useDashboardWS(): void {
    const adapterRef = useRef<ProtocolAdapter | null>(null)

    useEffect(() => {
        const {
            setConnectionStatus,
            applyFullUpdate,
            applyMergedPayload,
        } = useDashboardStore.getState()

        const adapter = new ProtocolAdapter({
            url: runtimeConfig.wsUrl,
            store: { setConnectionStatus, applyFullUpdate, applyMergedPayload },
            initialReconnectDelayMs: RECONNECT_DELAY_MS,
            maxReconnectDelayMs: MAX_RECONNECT_DELAY_MS,
        })
        adapter.setPayloadGetter(() => useDashboardStore.getState().payload)

        adapterRef.current = adapter
        ConnectionMonitor.start()
        adapter.connect()

        return () => {
            adapter.disconnect()
            ConnectionMonitor.stop()
            adapterRef.current = null
        }
    }, [])
}

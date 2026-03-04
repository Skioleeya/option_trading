/**
 * l4_frontend — ProtocolAdapter (Phase 1: Protocol & State Decoupling)
 * ─────────────────────────────────────────────────────────────────────
 * Pure WebSocket transport layer. No React, no hooks, no side effects
 * beyond WebSocket I/O and store writes.
 *
 * Responsibilities:
 *   • WebSocket lifecycle (open / close / reconnect with exponential backoff)
 *   • Message routing:
 *       keepalive          → skip
 *       dashboard_delta    → DeltaDecoder.applyPatch → store.applyMergedPayload
 *       dashboard_update / dashboard_init → store.applyFullUpdate
 *   • Connection status propagation → store.setConnectionStatus
 *   • Binary/JSON auto-detect (Phase 1: JSON only; binary hook is a no-op
 *     that logs the frame type for future Protobuf cutover)
 *
 * Usage (from useDashboardWS):
 *   const adapter = new ProtocolAdapter({ url: WS_URL, store })
 *   adapter.connect()
 *   // ...
 *   adapter.disconnect()
 */

import type { DashboardState } from '../store/dashboardStore'
import type { DashboardPayload } from '../types/dashboard'
import { DeltaDecoder } from './deltaDecoder'
import { ConnectionMonitor } from '../observability/connectionMonitor'

// ─────────────────────────────────────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────────────────────────────────────

export interface ProtocolAdapterConfig {
    url: string
    store: Pick<
        DashboardState,
        'setConnectionStatus' | 'applyFullUpdate' | 'applyMergedPayload'
    >
    /** Initial reconnect delay in ms (default: 2000) */
    initialReconnectDelayMs?: number
    /** Maximum reconnect delay in ms (default: 30000) */
    maxReconnectDelayMs?: number
}

// ─────────────────────────────────────────────────────────────────────────────
// Adapter
// ─────────────────────────────────────────────────────────────────────────────

export class ProtocolAdapter {
    private readonly url: string
    private readonly store: ProtocolAdapterConfig['store']
    private readonly initialReconnectDelayMs: number
    private readonly maxReconnectDelayMs: number

    private ws: WebSocket | null = null
    private reconnectDelayMs: number
    private reconnectTimer: ReturnType<typeof setTimeout> | null = null
    private active = false

    constructor(config: ProtocolAdapterConfig) {
        this.url = config.url
        this.store = config.store
        this.initialReconnectDelayMs = config.initialReconnectDelayMs ?? 2000
        this.maxReconnectDelayMs = config.maxReconnectDelayMs ?? 30_000
        this.reconnectDelayMs = this.initialReconnectDelayMs
    }

    // ── Public API ─────────────────────────────────────────────────────────────

    connect(): void {
        this.active = true
        this._openSocket()
    }

    disconnect(): void {
        this.active = false
        this._clearReconnectTimer()
        this.ws?.close()
        this.ws = null
    }

    sendPing(): void {
        // 1 === WebSocket.OPEN (using literal for test-environment mock compat)
        if (this.ws !== null && this.ws.readyState === 1) {
            this.ws.send('ping')
        }
    }

    // ── Private helpers ────────────────────────────────────────────────────────

    private _openSocket(): void {
        if (!this.active) return

        if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
            return
        }

        this.store.setConnectionStatus('connecting')
        ConnectionMonitor.onWsConnecting()
        this._clearReconnectTimer()

        const ws = new WebSocket(this.url)
        this.ws = ws

        // Phase 1: JSON-only. Binary frames are logged for future Protobuf work.
        ws.binaryType = 'arraybuffer'

        ws.onopen = this.handleOpen
        ws.onmessage = this.handleMessage
        ws.onclose = this.handleClose
        ws.onerror = this.handleError
    }

    private handleOpen = () => {
        if (!this.active) return
        console.info('[L4 ProtocolAdapter] Connected to backend.')
        this.store.setConnectionStatus('connected')
        this.reconnectDelayMs = this.initialReconnectDelayMs
        ConnectionMonitor.onWsOpen()
    }

    private handleMessage = (evt: MessageEvent) => {
        if (!this.active) return

        // Binary frame detection (Phase 1: log only; Phase 3 will add Protobuf)
        if (evt.data instanceof ArrayBuffer) {
            console.debug(
                '[L4 ProtocolAdapter] Binary frame received (%d bytes) — ' +
                'Protobuf decoder not yet active; frame skipped.',
                evt.data.byteLength
            )
            return
        }

        this._handleTextMessage(evt.data as string)
    }

    private handleClose = (evt: CloseEvent) => {
        if (!this.active) return
        this.store.setConnectionStatus('disconnected')
        const delay = this.reconnectDelayMs
        console.warn(
            `[L4 ProtocolAdapter] Disconnected. Reconnecting in ${delay}ms.`
        )
        this.reconnectDelayMs = Math.min(delay * 1.5, this.maxReconnectDelayMs)
        this._scheduleReconnect(delay)
        ConnectionMonitor.onWsClose(evt.code)
    }

    private handleError = () => {
        this.ws?.close()
        ConnectionMonitor.onWsError()
    }

    private _handleTextMessage(raw: string): void {
        const msg = DeltaDecoder.parseMessage(raw)
        if (msg === null) return

        // ── keepalive ────────────────────────────────────────────────────────────
        if (DeltaDecoder.isKeepalive(msg)) {
            ConnectionMonitor.onKeepalive()
            // Optional: trigger state update for debugging connection status
            return
        }

        // ── dashboard_delta (JSON-Patch) ─────────────────────────────────────────
        if (DeltaDecoder.isDelta(msg)) {
            const data = msg as any
            const current = this._getCurrentPayload()
            if (!current) {
                // No baseline to patch against — treat as a full update fallback
                console.warn(
                    '[L4 ProtocolAdapter] Delta received before full update; skipping.'
                )
                return
            }

            const result = DeltaDecoder.applyPatch(current, data.patch, {
                heartbeat_timestamp: data.heartbeat_timestamp,
                timestamp: data.timestamp,
            })

            if (result.ok) {
                this.store.applyMergedPayload(result.value)
            } else {
                console.error(
                    '[L4 ProtocolAdapter] Failed to apply JSON patch:',
                    result.error,
                    'Patch:',
                    data.patch
                )
            }
            return
        }

        // ── dashboard_update / dashboard_init (full snapshot) ────────────────────
        this.store.applyFullUpdate(msg as DashboardPayload)
        ConnectionMonitor.onFullPayload()
    }

    /**
     * Read the current payload from the store without importing the full
     * Zustand store (to keep this module store-agnostic and testable with mocks).
     */
    private _getCurrentPayload(): DashboardPayload | null {
        // The store reference is typed as the minimal interface we need.
        // We read payload by calling getState() if available, or fall back
        // to a snapshot captured at applyFullUpdate time. Since the store
        // exposes applyFullUpdate / applyMergedPayload but not read, we
        // delegate the read concern to the caller (useDashboardWS) via the
        // getPayload callback.
        return this._payloadGetter?.() ?? null
    }

    /** Inject a getter at construction time for current payload (testable). */
    private _payloadGetter: (() => DashboardPayload | null) | null = null

    /** Called by useDashboardWS to wire up the payload reader from the store. */
    setPayloadGetter(fn: () => DashboardPayload | null): void {
        this._payloadGetter = fn
    }

    private _scheduleReconnect(delayMs: number): void {
        this._clearReconnectTimer()
        this.reconnectTimer = setTimeout(() => this._openSocket(), delayMs)
    }

    private _clearReconnectTimer(): void {
        if (this.reconnectTimer !== null) {
            clearTimeout(this.reconnectTimer)
            this.reconnectTimer = null
        }
    }
}

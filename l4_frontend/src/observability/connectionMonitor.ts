/**
 * l4_frontend — Connection Monitor (Phase 5)
 * ──────────────────────────────────────────
 * 5-State Connection Machine for institutional-grade observability.
 * States:
 *   1. DISCONNECTED  (initial/fatal)
 *   2. CONNECTING    (negotiating)
 *   3. AWAIT_STATE   (ws open, waiting for full payload)
 *   4. RUNNING       (streaming deltas)
 *   5. STALLED       (heartbeat timeout)
 */

import { useDashboardStore } from '../store/dashboardStore'
import { L4Rum } from './l4_rum'

export type ConnectionState =
    | 'DISCONNECTED'
    | 'CONNECTING'
    | 'AWAIT_STATE'
    | 'RUNNING'
    | 'STALLED'

class ConnectionMonitorImpl {
    private currentState: ConnectionState = 'DISCONNECTED'
    private lastPongAt: number = 0
    private heartbeatInterval: ReturnType<typeof setInterval> | null = null

    // Config
    private readonly STALL_THRESHOLD_MS = 3000

    // Optional callback for UI if needed natively
    public onStateChange?: (state: ConnectionState) => void

    start() {
        this.stop()
        this.heartbeatInterval = setInterval(() => this.checkStall(), 1000)
        console.debug('[L4 ConnectionMonitor] Started')
    }

    stop() {
        if (this.heartbeatInterval) clearInterval(this.heartbeatInterval)
        this.heartbeatInterval = null
        this.transition('DISCONNECTED')
    }

    private transition(next: ConnectionState, reason?: string) {
        if (this.currentState === next) return
        const prev = this.currentState
        this.currentState = next

        console.log(`[L4 ConnectionMonitor] ${prev} → ${next} ${reason ? `(${reason})` : ''}`)

        // Sync with top-level store for UI connection color
        if (next === 'RUNNING' || next === 'AWAIT_STATE') {
            useDashboardStore.getState().setConnectionStatus('connected')
        } else if (next === 'CONNECTING') {
            useDashboardStore.getState().setConnectionStatus('connecting')
        } else {
            useDashboardStore.getState().setConnectionStatus('disconnected')
        }

        if (this.onStateChange) this.onStateChange(next)
    }

    // --- Network Events ---

    onWsConnecting() {
        this.transition('CONNECTING')
    }

    onWsOpen() {
        this.lastPongAt = Date.now()
        this.transition('AWAIT_STATE')
    }

    onWsClose(code: number) {
        this.transition('DISCONNECTED', `closed code=${code}`)
    }

    onWsError() {
        this.transition('DISCONNECTED', 'ws error')
    }

    // --- App Events ---

    onFullPayload() {
        if (this.currentState === 'AWAIT_STATE' || this.currentState === 'STALLED') {
            this.transition('RUNNING', 'full payload received')
        }
    }

    onKeepalive() {
        this.lastPongAt = Date.now()
        if (this.currentState === 'STALLED') {
            this.transition('RUNNING', 'recovered via keepalive')
        }
    }

    // --- Internal Loop ---

    private checkStall() {
        if (this.currentState !== 'RUNNING' && this.currentState !== 'AWAIT_STATE') return

        const now = Date.now()
        if (now - this.lastPongAt > this.STALL_THRESHOLD_MS) {
            L4Rum.recordStall() // Log to RUM
            this.transition('STALLED', 'heartbeat timeout')
        }
    }

    public getState() {
        return this.currentState
    }
}

export const ConnectionMonitor = new ConnectionMonitorImpl()

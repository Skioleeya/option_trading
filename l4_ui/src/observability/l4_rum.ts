/// <reference types="vite/client" />
/**
 * l4_ui — L4 Real-User Monitoring (Phase 2: Observability)
 * ───────────────────────────────────────────────────────────────
 * Lightweight, zero-dependency RUM metrics collection.
 *
 * All metrics are collected using browser-native APIs only:
 *   • Performance API (marks + measures)
 *   • requestAnimationFrame (FPS)
 *   • performance.memory (V8 heap — Chrome only, graceful fallback)
 *
 * Design: side-effect-free singleton with graceful no-op if running
 * in an environment without browser APIs (SSR/test).
 *
 * Metrics emitted (aligned with L4_FRONTEND.md §12):
 *   l4.ws_msg_received   — mark: WS message arrived
 *   l4.ws_msg_processed  — mark: store updated (after decode + patch)
 *   l4.ws_msg_to_render  — measure: msg → DOM update latency
 *   l4.frame_rate        — gauge: FPS sampled every 2s
 *   l4.memory_usage_mb   — gauge: JS heap (Chrome only)
 *   l4.ws_reconnect      — counter: incremented on each reconnect
 *   l4.fmp               — mark: First Meaningful Paint
 */

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface RumSnapshot {
    fps: number
    memoryMb: number | null
    reconnectCount: number
    lastMsgLatencyMs: number | null
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton implementation
// ─────────────────────────────────────────────────────────────────────────────

class L4RumImpl {
    private reconnectCount = 0
    private lastMsgLatencyMs: number | null = null
    private fpsGauge = 0
    private fpsFrameCount = 0
    private fpsLastTs = 0
    private rafHandle: number | null = null
    private readonly enabled: boolean

    constructor() {
        // Guard: only activate in browser environment
        this.enabled = typeof window !== 'undefined' && typeof performance !== 'undefined'
        if (this.enabled) {
            this._startFpsLoop()
        }
    }

    // ── Public API ─────────────────────────────────────────────────────────────

    /** Mark: a WS message was received (call at WS.onmessage entry). */
    markMsgReceived(): void {
        if (!this.enabled) return
        performance.mark('l4.ws_msg_received')
    }

    /** Mark: store was updated after decode (call after applyFullUpdate/applyMergedPayload). */
    markMsgProcessed(): void {
        if (!this.enabled) return
        try {
            performance.mark('l4.ws_msg_processed')
            const measure = performance.measure(
                'l4.ws_msg_to_render',
                'l4.ws_msg_received',
                'l4.ws_msg_processed'
            )
            this.lastMsgLatencyMs = measure.duration
            if (import.meta.env.DEV && measure.duration > 10) {
                console.debug(
                    `[L4 RUM] ws_msg_to_render: ${measure.duration.toFixed(2)}ms`
                )
            }
        } catch {
            // Marks may not align if processed without a preceding received mark
        }
    }

    /** Mark: First Meaningful Paint (call once in App.tsx useEffect). */
    markFmp(): void {
        if (!this.enabled) return
        performance.mark('l4.fmp')
        if (import.meta.env.DEV) {
            const nav = performance.getEntriesByType('navigation')[0] as
                | PerformanceNavigationTiming
                | undefined
            if (nav) {
                const fmp = performance.now() - nav.startTime
                console.info(`[L4 RUM] FMP: ${fmp.toFixed(0)}ms`)
            }
        }
    }

    /** Increment reconnect counter. */
    recordReconnect(): void {
        this.reconnectCount++
        if (import.meta.env.DEV) {
            console.warn(`[L4 RUM] Reconnect #${this.reconnectCount}`)
        }
    }

    /** Record a connection stall. */
    recordStall(): void {
        if (import.meta.env.DEV) {
            console.warn(`[L4 RUM] Connection stalled (heartbeat timeout)`)
        }
    }

    /** Read current RUM snapshot. */
    snapshot(): RumSnapshot {
        return {
            fps: this.fpsGauge,
            memoryMb: this._readMemoryMb(),
            reconnectCount: this.reconnectCount,
            lastMsgLatencyMs: this.lastMsgLatencyMs,
        }
    }

    /** Stop FPS loop (call on app unmount). */
    dispose(): void {
        if (this.rafHandle !== null) {
            cancelAnimationFrame(this.rafHandle)
            this.rafHandle = null
        }
    }

    // ── Private ────────────────────────────────────────────────────────────────

    private _startFpsLoop(): void {
        const SAMPLE_INTERVAL_MS = 2000

        const tick = (ts: number) => {
            this.fpsFrameCount++
            if (this.fpsLastTs === 0) this.fpsLastTs = ts

            const elapsed = ts - this.fpsLastTs
            if (elapsed >= SAMPLE_INTERVAL_MS) {
                this.fpsGauge = Math.round((this.fpsFrameCount / elapsed) * 1000)
                this.fpsFrameCount = 0
                this.fpsLastTs = ts

                if (import.meta.env.DEV && this.fpsGauge < 50) {
                    console.warn(`[L4 RUM] Low FPS detected: ${this.fpsGauge}fps`)
                }
            }

            this.rafHandle = requestAnimationFrame(tick)
        }

        this.rafHandle = requestAnimationFrame(tick)
    }

    private _readMemoryMb(): number | null {
        try {
            // performance.memory is V8/Chrome-only; graceful fallback
            const mem = (performance as any).memory
            if (mem && typeof mem.usedJSHeapSize === 'number') {
                return Math.round(mem.usedJSHeapSize / 1024 / 1024)
            }
        } catch {
            // intentional no-op
        }
        return null
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Export singleton
// ─────────────────────────────────────────────────────────────────────────────

export const L4Rum = new L4RumImpl()

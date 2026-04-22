/// <reference types="vite/client" />
import type { DashboardPayload } from '../types/dashboard'

interface RumSnapshot {
    fps: number
    memoryMb: number | null
    reconnectCount: number
    lastMsgLatencyMs: number | null
    lastStoreToPaintMs: number | null
    lastWireLagMs: number | null
    lastSourceToPaintObservedMs: number | null
}

class L4RumImpl {
    private reconnectCount = 0
    private lastMsgLatencyMs: number | null = null
    private lastStoreToPaintMs: number | null = null
    private lastWireLagMs: number | null = null
    private lastSourceToPaintObservedMs: number | null = null
    private fpsGauge = 0
    private fpsFrameCount = 0
    private fpsLastTs = 0
    private rafHandle: number | null = null
    private profilingEnabled = false
    private readonly enabled: boolean

    constructor() {
        this.enabled = typeof window !== 'undefined' && typeof performance !== 'undefined'
    }

    setProfilingEnabled(enabled: boolean): void {
        if (!this.enabled) return
        if (this.profilingEnabled === enabled) return
        this.profilingEnabled = enabled
        if (enabled) {
            this._startFpsLoop()
            return
        }
        this._stopFpsLoop()
        this.fpsGauge = 0
        this.fpsFrameCount = 0
        this.fpsLastTs = 0
        this.lastMsgLatencyMs = null
        this.lastStoreToPaintMs = null
        this.lastWireLagMs = null
        this.lastSourceToPaintObservedMs = null
    }

    markMsgReceived(): void {
        if (!this.enabled || !this.profilingEnabled) return
        performance.mark('l4.ws_msg_received')
    }

    markMsgProcessed(payload?: DashboardPayload | null): void {
        if (!this.enabled || !this.profilingEnabled) return
        try {
            performance.mark('l4.ws_msg_processed')
            const measure = performance.measure(
                'l4.ws_msg_to_store',
                'l4.ws_msg_received',
                'l4.ws_msg_processed',
            )
            this.lastMsgLatencyMs = measure.duration
            this.lastWireLagMs = this._resolveWireLagMs(payload)
            const processedAt = performance.now()
            requestAnimationFrame(() => {
                if (!this.profilingEnabled) return
                const storeToPaintMs = performance.now() - processedAt
                this.lastStoreToPaintMs = storeToPaintMs
                this.lastSourceToPaintObservedMs = (
                    (this.lastWireLagMs ?? 0) +
                    (this.lastMsgLatencyMs ?? 0) +
                    storeToPaintMs
                )
            })
            if (import.meta.env.DEV && measure.duration > 10) {
                console.debug(`[L4 RUM] ws_msg_to_store: ${measure.duration.toFixed(2)}ms`)
            }
        } catch {
            // marks may not align if profiling toggled mid-stream
        }
    }

    markFmp(): void {
        if (!this.enabled) return
        performance.mark('l4.fmp')
        if (!import.meta.env.DEV) return
        const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined
        if (!nav) return
        const fmp = performance.now() - nav.startTime
        console.info(`[L4 RUM] FMP: ${fmp.toFixed(0)}ms`)
    }

    recordReconnect(): void {
        this.reconnectCount += 1
        if (import.meta.env.DEV) {
            console.warn(`[L4 RUM] Reconnect #${this.reconnectCount}`)
        }
    }

    recordStall(): void {
        if (import.meta.env.DEV) {
            console.warn('[L4 RUM] Connection stalled (heartbeat timeout)')
        }
    }

    snapshot(): RumSnapshot {
        return {
            fps: this.fpsGauge,
            memoryMb: this._readMemoryMb(),
            reconnectCount: this.reconnectCount,
            lastMsgLatencyMs: this.lastMsgLatencyMs,
            lastStoreToPaintMs: this.lastStoreToPaintMs,
            lastWireLagMs: this.lastWireLagMs,
            lastSourceToPaintObservedMs: this.lastSourceToPaintObservedMs,
        }
    }

    dispose(): void {
        this._stopFpsLoop()
    }

    private _startFpsLoop(): void {
        if (this.rafHandle !== null) return
        const sampleIntervalMs = 2000
        const tick = (ts: number) => {
            if (!this.profilingEnabled) {
                this._stopFpsLoop()
                return
            }
            this.fpsFrameCount += 1
            if (this.fpsLastTs === 0) this.fpsLastTs = ts
            const elapsed = ts - this.fpsLastTs
            if (elapsed >= sampleIntervalMs) {
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

    private _stopFpsLoop(): void {
        if (this.rafHandle === null) return
        cancelAnimationFrame(this.rafHandle)
        this.rafHandle = null
    }

    private _readMemoryMb(): number | null {
        try {
            const memory = (performance as Performance & { memory?: { usedJSHeapSize?: number } }).memory
            if (memory && typeof memory.usedJSHeapSize === 'number') {
                return Math.round(memory.usedJSHeapSize / 1024 / 1024)
            }
        } catch {
            // intentional no-op
        }
        return null
    }

    private _resolveWireLagMs(payload?: DashboardPayload | null): number | null {
        const quoteLane = payload?.governor_telemetry && typeof payload.governor_telemetry === 'object'
            ? (payload.governor_telemetry as Record<string, unknown>).quote_lane
            : null
        if (quoteLane && typeof quoteLane === 'object') {
            const direct = (quoteLane as Record<string, unknown>).wire_emit_lag_ms
            if (typeof direct === 'number' && Number.isFinite(direct)) {
                return direct
            }
        }
        const sourceTs = payload?.data_timestamp
        const wireTs = payload?.broadcast_timestamp
        if (typeof sourceTs !== 'string' || typeof wireTs !== 'string') return null
        const sourceMs = Date.parse(sourceTs)
        const wireMs = Date.parse(wireTs)
        if (!Number.isFinite(sourceMs) || !Number.isFinite(wireMs)) return null
        return Math.max(0, wireMs - sourceMs)
    }
}

export const L4Rum = new L4RumImpl()

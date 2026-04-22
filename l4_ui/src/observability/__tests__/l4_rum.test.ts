import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { L4Rum } from '../l4_rum'

describe('L4Rum', () => {
    const originalRaf = globalThis.requestAnimationFrame
    const originalCancel = globalThis.cancelAnimationFrame
    let frameCallbacks: FrameRequestCallback[] = []

    beforeEach(() => {
        vi.restoreAllMocks()
        frameCallbacks = []
        let nextFrameId = 1
        globalThis.requestAnimationFrame = vi.fn((cb: FrameRequestCallback) => {
            frameCallbacks.push(cb)
            return nextFrameId += 1
        })
        globalThis.cancelAnimationFrame = vi.fn()
    })

    afterEach(() => {
        L4Rum.setProfilingEnabled(false)
        globalThis.requestAnimationFrame = originalRaf
        globalThis.cancelAnimationFrame = originalCancel
        vi.restoreAllMocks()
    })

    it('does not emit performance marks while profiling is disabled', () => {
        const markSpy = vi.spyOn(performance, 'mark')
        const measureSpy = vi.spyOn(performance, 'measure')

        L4Rum.setProfilingEnabled(false)
        L4Rum.markMsgReceived()
        L4Rum.markMsgProcessed(null)

        expect(markSpy).not.toHaveBeenCalled()
        expect(measureSpy).not.toHaveBeenCalled()
        expect(L4Rum.snapshot().lastMsgLatencyMs).toBeNull()
    })

    it('records websocket and paint timings only when profiling is enabled', () => {
        vi.spyOn(performance, 'mark').mockImplementation(() => ({
            detail: null,
            entryType: 'mark',
            name: 'mock-mark',
            startTime: 0,
            duration: 0,
            toJSON: () => ({}),
        }) as PerformanceMark)
        vi.spyOn(performance, 'measure').mockReturnValue({ duration: 7.5 } as PerformanceMeasure)

        L4Rum.setProfilingEnabled(true)
        L4Rum.markMsgReceived()
        L4Rum.markMsgProcessed({
            data_timestamp: '2026-04-21T13:30:00.000Z',
            broadcast_timestamp: '2026-04-21T13:30:00.012Z',
        } as any)
        frameCallbacks.splice(0).forEach((callback) => callback(16))

        const snapshot = L4Rum.snapshot()
        expect(snapshot.lastMsgLatencyMs).toBe(7.5)
        expect(snapshot.lastWireLagMs).toBe(12)
        expect(snapshot.lastStoreToPaintMs).not.toBeNull()
        expect(snapshot.lastSourceToPaintObservedMs).not.toBeNull()

        L4Rum.setProfilingEnabled(false)
        const reset = L4Rum.snapshot()
        expect(reset.lastMsgLatencyMs).toBeNull()
        expect(reset.lastWireLagMs).toBeNull()
        expect(reset.lastStoreToPaintMs).toBeNull()
        expect(reset.lastSourceToPaintObservedMs).toBeNull()
    })
})

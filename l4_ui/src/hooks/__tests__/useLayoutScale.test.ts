import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useLayoutScale } from '../useLayoutScale'

type ResizeListener = (event: Event) => void

interface MockVisualViewport {
    width: number
    height: number
    addEventListener: (type: string, listener: ResizeListener) => void
    removeEventListener: (type: string, listener: ResizeListener) => void
}

function setWindowSize(width: number, height: number): void {
    Object.defineProperty(window, 'innerWidth', {
        configurable: true,
        writable: true,
        value: width,
    })
    Object.defineProperty(window, 'innerHeight', {
        configurable: true,
        writable: true,
        value: height,
    })
}

function createMockVisualViewport(width: number, height: number): {
    viewport: MockVisualViewport
    emitResize: () => void
} {
    const listeners = new Set<ResizeListener>()

    const viewport: MockVisualViewport = {
        width,
        height,
        addEventListener: (type, listener) => {
            if (type === 'resize') {
                listeners.add(listener)
            }
        },
        removeEventListener: (type, listener) => {
            if (type === 'resize') {
                listeners.delete(listener)
            }
        },
    }

    const emitResize = () => {
        const evt = new Event('resize')
        listeners.forEach((listener) => listener(evt))
    }

    return { viewport, emitResize }
}

describe('useLayoutScale', () => {
    beforeEach(() => {
        vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
            cb(0)
            return 1
        })
        vi.stubGlobal('cancelAnimationFrame', () => undefined)
        Object.defineProperty(window, 'visualViewport', {
            configurable: true,
            value: undefined,
        })
    })

    afterEach(() => {
        vi.unstubAllGlobals()
    })

    it('computes initial scale from fixed base resolution', () => {
        setWindowSize(960, 540)

        const { result } = renderHook(() => useLayoutScale())

        expect(result.current.scale).toBe(0.5)
        expect(result.current.percent).toBe(50)
        expect(result.current.profile).toBe('secondary_compact')
    })

    it('returns 100 percent when viewport matches fixed baseline', () => {
        setWindowSize(1920, 1080)
        const { result } = renderHook(() => useLayoutScale())

        expect(result.current.scale).toBe(1)
        expect(result.current.percent).toBe(100)
        expect(result.current.profile).toBe('primary_standard')
    })

    it('applies upper clamp at 125 percent', () => {
        setWindowSize(1000, 1000)
        const { result } = renderHook(() => useLayoutScale())

        setWindowSize(3000, 3000)
        act(() => {
            window.dispatchEvent(new Event('resize'))
        })

        expect(result.current.scale).toBe(1.25)
        expect(result.current.percent).toBe(125)
        expect(result.current.profile).toBe('primary_standard')
    })

    it('syncs with visualViewport resize', () => {
        setWindowSize(1600, 900)
        const { viewport, emitResize } = createMockVisualViewport(1600, 900)
        Object.defineProperty(window, 'visualViewport', {
            configurable: true,
            value: viewport,
        })

        const { result } = renderHook(() => useLayoutScale())

        expect(result.current.profile).toBe('primary_standard')

        viewport.width = 1280
        viewport.height = 720

        act(() => {
            emitResize()
        })

        expect(result.current.scale).toBeCloseTo(2 / 3)
        expect(result.current.percent).toBe(67)
        expect(result.current.profile).toBe('secondary_compact')
    })
})

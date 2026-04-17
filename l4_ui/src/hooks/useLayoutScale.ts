import { useEffect, useRef, useState } from 'react'
import { computeLayoutScale, sanitizeDimension, type LayoutScaleState } from '../lib/layoutScale'

const SCALE_EPSILON = 0.001

function readViewportSize(): { width: number; height: number } {
    const visualViewport = window.visualViewport
    return {
        width: sanitizeDimension(visualViewport?.width ?? window.innerWidth),
        height: sanitizeDimension(visualViewport?.height ?? window.innerHeight),
    }
}

export function useLayoutScale(): LayoutScaleState {
    const [state, setState] = useState<LayoutScaleState>(() => {
        if (typeof window === 'undefined') {
            return { scale: 1, percent: 100, profile: 'primary_standard' }
        }
        return computeLayoutScale(readViewportSize())
    })
    const rafIdRef = useRef<number | null>(null)

    useEffect(() => {
        const computeNextState = (): void => {
            const next = computeLayoutScale(readViewportSize())
            setState((prev) => {
                if (Math.abs(prev.scale - next.scale) < SCALE_EPSILON && prev.percent === next.percent) {
                    return prev
                }
                return next
            })
        }

        const scheduleCompute = (): void => {
            if (rafIdRef.current !== null) {
                return
            }
            rafIdRef.current = window.requestAnimationFrame(() => {
                rafIdRef.current = null
                computeNextState()
            })
        }

        computeNextState()
        window.addEventListener('resize', scheduleCompute)

        const visualViewport = window.visualViewport
        visualViewport?.addEventListener('resize', scheduleCompute)

        return () => {
            window.removeEventListener('resize', scheduleCompute)
            visualViewport?.removeEventListener('resize', scheduleCompute)
            if (rafIdRef.current !== null) {
                window.cancelAnimationFrame(rafIdRef.current)
            }
        }
    }, [])

    return state
}

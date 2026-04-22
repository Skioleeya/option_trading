import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useDashboardStore } from '../../../store/dashboardStore'

const createAtmChartRuntimeMock = vi.fn()

vi.mock('../chartEngineAdapter', () => ({
    createAtmChartRuntime: (...args: unknown[]) => createAtmChartRuntimeMock(...args),
}))

import { AtmDecayChart } from '../AtmDecayChart'

const MARKET_ROW = {
    strike: 709,
    locked_at: '2026-04-21T13:29:59.000Z',
    timestamp: '2026-04-21T13:30:00.000Z',
    straddle_pct: 0.01,
    call_pct: 0.02,
    put_pct: -0.01,
}

function setDocumentVisibility(state: 'visible' | 'hidden'): void {
    Object.defineProperty(document, 'visibilityState', {
        configurable: true,
        get: () => state,
    })
}

function createSeriesStub() {
    return {
        setData: vi.fn(),
        update: vi.fn(),
        applyOptions: vi.fn(),
    }
}

function createChartRuntimeStub() {
    const rawSeries = [createSeriesStub(), createSeriesStub(), createSeriesStub()]
    const smoothSeries = [createSeriesStub(), createSeriesStub(), createSeriesStub()]
    const setVisibleRange = vi.fn()
    const fitContent = vi.fn()

    return {
        chart: {
            subscribeCrosshairMove: vi.fn(),
            unsubscribeCrosshairMove: vi.fn(),
            remove: vi.fn(),
            applyOptions: vi.fn(),
            timeScale: () => ({
                setVisibleRange,
                fitContent,
            }),
        },
        rawSeries,
        smoothSeries,
        rawMarkersPlugin: { setMarkers: vi.fn(), detach: vi.fn() },
        smoothMarkersPlugin: { setMarkers: vi.fn(), detach: vi.fn() },
        helpers: {
            setVisibleRange,
            fitContent,
        },
    }
}

describe('AtmDecayChart degraded mode', () => {
    beforeEach(() => {
        createAtmChartRuntimeMock.mockReset()
        useDashboardStore.setState({
            atmHistory: [],
            atmHistoryTradeDateKey: null,
            atmHistoryLastTimestamp: null,
        } as never)
        setDocumentVisibility('visible')
        vi.stubGlobal('ResizeObserver', class {
            observe = vi.fn()
            disconnect = vi.fn()
        })
    })

    afterEach(() => {
        cleanup()
        vi.restoreAllMocks()
        vi.unstubAllGlobals()
    })

    it('keeps component mounted and shows degraded overlay when chart init fails', () => {
        createAtmChartRuntimeMock.mockImplementation(() => {
            throw new Error('chart-init-failed')
        })
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

        expect(() => render(<AtmDecayChart data={[]} />)).not.toThrow()
        expect(screen.getByTestId('atm-chart-degraded')).toHaveTextContent('CENTER CHART DEGRADED (INIT)')
        expect(errorSpy).toHaveBeenCalled()
    })

    it('replays the latest store state when the tab becomes visible again', () => {
        const runtime = createChartRuntimeStub()
        createAtmChartRuntimeMock.mockReturnValue(runtime)
        setDocumentVisibility('hidden')

        render(<AtmDecayChart data={[MARKET_ROW]} />)

        expect(runtime.rawSeries[0].setData).not.toHaveBeenCalled()
        expect(runtime.smoothSeries[0].setData).not.toHaveBeenCalled()

        setDocumentVisibility('visible')
        act(() => {
            document.dispatchEvent(new Event('visibilitychange'))
        })

        expect(runtime.rawSeries[0].setData).toHaveBeenCalledTimes(1)
        expect(runtime.smoothSeries[0].setData).toHaveBeenCalledTimes(1)
        expect(runtime.helpers.setVisibleRange).toHaveBeenCalledTimes(1)
    })
})

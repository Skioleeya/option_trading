import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, render, screen } from '@testing-library/react'
import { useDashboardStore } from '../../store/dashboardStore'

vi.mock('../../hooks/useDashboardWS', () => ({
    useDashboardWS: () => undefined,
}))

vi.mock('../../observability/l4_rum', () => ({
    L4Rum: {
        markFmp: vi.fn(),
        setProfilingEnabled: vi.fn(),
        snapshot: vi.fn(() => ({
            fps: 60,
            memoryMb: 64,
            reconnectCount: 0,
            lastMsgLatencyMs: null,
            lastStoreToPaintMs: null,
            lastWireLagMs: null,
            lastSourceToPaintObservedMs: null,
        })),
    },
}))

vi.mock('../../alerts/alertEngine', () => ({
    AlertEngine: {
        start: vi.fn(),
        stop: vi.fn(),
    },
}))

vi.mock('../center/Header', () => ({ Header: () => <div data-testid="stub-header" /> }))
vi.mock('../center/GexStatusBar', () => ({ GexStatusBar: () => <div data-testid="stub-gex" /> }))
vi.mock('../center/AtmDecayOverlay', () => ({ AtmDecayOverlay: () => <div data-testid="stub-overlay" /> }))
vi.mock('../left/LeftPanel', () => ({ LeftPanel: () => <div data-testid="stub-left" /> }))
vi.mock('../right/RightPanel', () => ({ RightPanel: () => <div data-testid="stub-right" /> }))
vi.mock('../center/AtmDecayChart', () => ({ AtmDecayChart: () => <div data-testid="stub-chart" /> }))
vi.mock('../AlertToast', () => ({ AlertToast: () => <div data-testid="stub-toast" /> }))
vi.mock('../CommandPalette', () => ({ CommandPalette: () => <div data-testid="stub-palette" /> }))
vi.mock('../DebugOverlay', () => ({ DebugOverlay: () => <div>L1 SIMD DIAGNOSTICS</div> }))

import { App, __appTestOnly } from '../App'

function buildEmptyHistoryResponse() {
    return {
        schema: 'v2',
        encoding: 'columnar-json',
        columns: [],
        rows: [],
        count: 0,
        date: '20260423',
    }
}

beforeEach(() => {
    vi.useFakeTimers()
    vi.stubEnv('DEV', true)
    Object.defineProperty(window, 'innerWidth', {
        configurable: true,
        writable: true,
        value: 1536,
    })
    Object.defineProperty(window, 'innerHeight', {
        configurable: true,
        writable: true,
        value: 864,
    })
    vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({
            ok: true,
            text: async () => '',
            json: async () => buildEmptyHistoryResponse(),
        }),
    )
})

afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    useDashboardStore.setState({
        payload: null,
        connectionStatus: 'connecting',
        spot: null,
        ivPct: null,
        atm: null,
        atmHistory: [],
        atmHistoryTradeDateKey: null,
        atmHistoryLastTimestamp: null,
    } as never)
})

describe('ATM history strict hydrate gate', () => {
    it('does not fast-fail on empty history outside RTH', async () => {
        vi.setSystemTime(new Date('2026-04-23T11:59:07Z'))

        render(<App />)

        await act(async () => {
            await Promise.resolve()
        })
        expect(screen.queryByText(/ATM HISTORY FAST-FAIL:/)).not.toBeInTheDocument()
        expect(useDashboardStore.getState().atmHistory).toEqual([])
        expect(__appTestOnly.isStrictAtmHistoryRequired(new Date('2026-04-23T11:59:07Z'))).toBe(false)
    })

    it('fast-fails on empty history during RTH', async () => {
        vi.setSystemTime(new Date('2026-04-23T14:31:00Z'))

        render(<App />)

        await act(async () => {
            await Promise.resolve()
        })
        expect(screen.getByText(/ATM HISTORY FAST-FAIL:/)).toBeInTheDocument()
        expect(screen.getByText(/ATM history is empty; persistence is required in strict mode\./)).toBeInTheDocument()
        expect(__appTestOnly.isStrictAtmHistoryRequired(new Date('2026-04-23T14:31:00Z'))).toBe(true)
    })
})

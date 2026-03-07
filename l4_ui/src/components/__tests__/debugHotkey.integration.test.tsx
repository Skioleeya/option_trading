import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useDashboardStore } from '../../store/dashboardStore'

vi.mock('../../hooks/useDashboardWS', () => ({
    useDashboardWS: () => undefined,
}))

vi.mock('../../observability/l4_rum', () => ({
    L4Rum: { markFmp: vi.fn() },
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
vi.mock('../left/WallMigration', () => ({ WallMigration: () => <div data-testid="stub-wall" /> }))
vi.mock('../left/DepthProfile', () => ({ DepthProfile: () => <div data-testid="stub-depth" /> }))
vi.mock('../left/MicroStats', () => ({ MicroStats: () => <div data-testid="stub-micro" /> }))
vi.mock('../right/DecisionEngine', () => ({ DecisionEngine: () => <div data-testid="stub-decision" /> }))
vi.mock('../right/TacticalTriad', () => ({ TacticalTriad: () => <div data-testid="stub-triad" /> }))
vi.mock('../right/SkewDynamics', () => ({ SkewDynamics: () => <div data-testid="stub-skew" /> }))
vi.mock('../right/ActiveOptions', () => ({ ActiveOptions: () => <div data-testid="stub-active" /> }))
vi.mock('../right/MtfFlow', () => ({ MtfFlow: () => <div data-testid="stub-mtf" /> }))
vi.mock('../center/AtmDecayChart', () => ({ AtmDecayChart: () => <div data-testid="stub-chart" /> }))
vi.mock('../AlertToast', () => ({ AlertToast: () => <div data-testid="stub-toast" /> }))

import { App } from '../App'

beforeEach(() => {
    vi.stubEnv('DEV', 'true')
    vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({
            json: async () => ({ history: [] }),
        })
    )
})

afterEach(() => {
    cleanup()
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
    } as any)
})

describe('Debug hotkey integration', () => {
    it('toggles debug overlay via Ctrl/Cmd + D command hotkey chain', async () => {
        render(<App />)

        expect(screen.queryByText('L1 SIMD DIAGNOSTICS')).not.toBeInTheDocument()

        fireEvent.keyDown(window, { key: 'd', ctrlKey: true })
        await waitFor(() => {
            expect(screen.getByText('L1 SIMD DIAGNOSTICS')).toBeInTheDocument()
        })

        fireEvent.keyDown(window, { key: 'D', metaKey: true })
        await waitFor(() => {
            expect(screen.queryByText('L1 SIMD DIAGNOSTICS')).not.toBeInTheDocument()
        })
    })
})

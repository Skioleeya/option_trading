import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { ActiveOptions } from '../right/ActiveOptions'
import { MicroStats } from '../left/MicroStats'
import { TacticalTriad } from '../right/TacticalTriad'
import type { ActiveOption, TacticalTriadState } from '../../types/dashboard'

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
vi.mock('../left/LeftPanel', () => ({ LeftPanel: () => <div data-testid="stub-left" /> }))
vi.mock('../right/RightPanel', () => ({ RightPanel: () => <div data-testid="stub-right" /> }))
vi.mock('../center/AtmDecayChart', () => ({ AtmDecayChart: () => <div data-testid="stub-chart" /> }))
vi.mock('../center/AtmDecayOverlay', () => ({ AtmDecayOverlay: () => <div data-testid="stub-overlay" /> }))
vi.mock('../center/GexStatusBar', () => ({ GexStatusBar: () => <div data-testid="stub-gex" /> }))
vi.mock('../AlertToast', () => ({ AlertToast: () => <div data-testid="stub-toast" /> }))
vi.mock('../CommandPalette', () => ({ CommandPalette: () => <div data-testid="stub-command" /> }))
vi.mock('../DebugOverlay', () => ({ DebugOverlay: () => <div data-testid="stub-debug" /> }))

import { App } from '../App'

const SAMPLE_OPTION: ActiveOption = {
    symbol: 'SPY',
    option_type: 'CALL',
    strike: 710,
    implied_volatility: 0.24,
    volume: 42000,
    turnover: 9200000,
    flow: 1350000,
    flow_score: 0.8,
    impact_index: 88123,
    is_sweep: true,
    flow_deg_formatted: '$1.35M',
    flow_volume_label: '42K',
    flow_color: 'text-accent-red',
    flow_glow: 'shadow-none',
    flow_intensity: 'HIGH',
    flow_direction: 'BULLISH',
}

const SAMPLE_TRIAD: TacticalTriadState = {
    vrp: {
        value: '-3.4%',
        state_label: 'BUY',
        color_class: 'text-accent-red',
        border_class: 'border-accent-red/40',
        bg_class: 'bg-accent-red/5',
        shadow_class: 'shadow-none',
        sub_intensity: 'HIGH',
        sub_label: 'BREAKOUT',
        animation: 'animate-pulse',
    },
    charm: {
        value: '-2.1',
        state_label: 'DECAYING',
        color_class: 'text-accent-green',
        border_class: 'border-accent-green/40',
        bg_class: 'bg-accent-green/5',
        shadow_class: 'shadow-none',
        sub_intensity: 'LOW',
        sub_label: 'ACCELERATING',
        animation: '',
    },
    svol: {
        value: '0.92',
        state_label: 'FLIP',
        color_class: 'text-accent-amber',
        border_class: 'border-accent-amber/40',
        bg_class: 'bg-accent-amber/5',
        shadow_class: 'shadow-none',
        sub_intensity: 'HIGH',
        sub_label: 'FLIP RISK',
        animation: 'animate-pulse',
    },
}

describe('small-window guardrails', () => {
    beforeEach(() => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                text: async () => '',
                json: async () => ({ history: [] }),
            }),
        )
    })

    afterEach(() => {
        cleanup()
        vi.unstubAllGlobals()
        vi.restoreAllMocks()
    })

    it('keeps the app shell clipped and leaves debug overlay unmounted by default', () => {
        const { container } = render(<App />)
        const root = container.firstElementChild as HTMLElement | null

        expect(root).not.toBeNull()
        expect(root?.className).toContain('h-screen')
        expect(root?.className).toContain('w-screen')
        expect(root?.className).toContain('overflow-hidden')
        expect(screen.getByTestId('stub-command')).toBeInTheDocument()
        expect(screen.getByTestId('stub-toast')).toBeInTheDocument()
        expect(screen.queryByTestId('stub-debug')).not.toBeInTheDocument()
    })

    it('renders active options as a nowrap compact table with compact IMP units', () => {
        const { container } = render(<ActiveOptions preferProp options={[SAMPLE_OPTION]} />)
        const table = container.querySelector('table')
        const impactCell = screen.getByText('88.1K')
        const flowCell = screen.getByText('$1.35M')

        expect(table).not.toBeNull()
        expect(table?.className).toContain('table-auto')
        expect(table?.querySelectorAll('th.whitespace-nowrap').length).toBeGreaterThan(0)
        expect(table?.querySelectorAll('td.whitespace-nowrap').length).toBeGreaterThan(0)
        expect(impactCell).toBeInTheDocument()
        expect(flowCell).toBeInTheDocument()
    })

    it('normalizes micro stats and triad cards to current semantic badge and border tokens', () => {
        const { container } = render(
            <>
                <MicroStats
                    preferProp
                    uiState={{
                        net_gex: { label: 'CALL LADDER', badge: 'positive' },
                        wall_dyn: { label: 'BREACH ↓', badge: 'badge-red' },
                        vanna: { label: 'NORMAL', badge: 'badge-neutral' },
                        momentum: { label: 'SHORT', badge: 'badge-green' },
                    }}
                />
                <TacticalTriad preferProp uiState={SAMPLE_TRIAD} />
            </>,
        )

        expect(screen.getByText('CALL LADDER')).toHaveClass('badge-red')
        expect(screen.getByText('BREACH ↓')).toHaveClass('badge-amber')
        expect(screen.getByText('SHORT')).toHaveClass('badge-green')

        const bullishCard = container.querySelector('.border-accent-red\\/40.bg-accent-red\\/5')
        const warningCard = container.querySelector('.border-accent-amber\\/40.bg-accent-amber\\/5')
        expect(bullishCard).not.toBeNull()
        expect(warningCard).not.toBeNull()
        expect(container.textContent).not.toContain('STATUS BAND')
        expect(container.textContent).not.toContain('ELEVATED_KEYWORDS')
    })
})

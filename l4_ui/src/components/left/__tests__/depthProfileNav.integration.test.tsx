import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, render, waitFor } from '@testing-library/react'
import { DepthProfile } from '../DepthProfile'
import { useDashboardStore } from '../../../store/dashboardStore'
import { buildCommandRegistry } from '../../../commands/commandRegistry'

function makeRow(strike: number) {
    return {
        strike,
        put_pct: 0.3,
        call_pct: 0.4,
        is_dominant_put: false,
        is_dominant_call: false,
        is_spot: false,
        is_flip: false,
    }
}

function seedStore(callWall: number | null, spot: number | null) {
    const rows = [makeRow(560), makeRow(565), makeRow(570)]
    useDashboardStore.setState({
        payload: {
            type: 'dashboard_update',
            timestamp: '2026-03-06T19:00:00Z',
            spot,
            agent_g: {
                agent: 'agent_g',
                signal: 'NEUTRAL',
                as_of: '2026-03-06T19:00:00Z',
                data: {
                    gamma_walls: { call_wall: callWall, put_wall: 555 },
                    gamma_flip_level: 558,
                    ui_state: {
                        depth_profile: rows,
                        macro_volume_map: {},
                        wall_migration: [],
                        micro_stats: {
                            net_gex: { label: '-', badge: 'badge-neutral' },
                            wall_dyn: { label: '-', badge: 'badge-neutral' },
                            vanna: { label: '-', badge: 'badge-neutral' },
                            momentum: { label: '-', badge: 'badge-neutral' },
                        },
                    },
                },
            },
        } as any,
        spot,
    })
}

afterEach(() => {
    cleanup()
})

describe('DepthProfile nav integration', () => {
    it('scrolls to nearest strike when wall target is not exact', async () => {
        seedStore(563, 560)
        const { container } = render(<DepthProfile />)

        const row560 = container.querySelector('[data-strike="560"]') as HTMLDivElement
        const row565 = container.querySelector('[data-strike="565"]') as HTMLDivElement
        const row570 = container.querySelector('[data-strike="570"]') as HTMLDivElement

        const s560 = vi.fn()
        const s565 = vi.fn()
        const s570 = vi.fn()
        Object.defineProperty(row560, 'scrollIntoView', { value: s560, configurable: true })
        Object.defineProperty(row565, 'scrollIntoView', { value: s565, configurable: true })
        Object.defineProperty(row570, 'scrollIntoView', { value: s570, configurable: true })

        const cmd = buildCommandRegistry().find((item) => item.id === 'nav_call_wall')
        await act(async () => {
            cmd?.action()
        })

        await waitFor(() => {
            expect(s565).toHaveBeenCalled()
        })
        expect(s560).not.toHaveBeenCalled()
        expect(s570).not.toHaveBeenCalled()
    })

    it('scrolls to spot target on nav_spot command', async () => {
        seedStore(565, 570)
        const { container } = render(<DepthProfile />)

        const row570 = container.querySelector('[data-strike="570"]') as HTMLDivElement
        const s570 = vi.fn()
        Object.defineProperty(row570, 'scrollIntoView', { value: s570, configurable: true })

        await act(async () => {
            window.dispatchEvent(new CustomEvent('l4:nav_spot'))
        })

        await waitFor(() => {
            expect(s570).toHaveBeenCalled()
        })
    })
})

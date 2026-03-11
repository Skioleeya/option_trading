import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { useDashboardStore } from '../../../store/dashboardStore'

const wallSpy = vi.fn()
const depthSpy = vi.fn()
const microSpy = vi.fn()

vi.mock('../WallMigration', () => ({
    WallMigration: (props: any) => {
        wallSpy(props)
        return <div data-testid="wall-migration" data-prefer={props.preferProp ? 'true' : 'false'} />
    },
}))

vi.mock('../DepthProfile', () => ({
    DepthProfile: (props: any) => {
        depthSpy(props)
        return <div data-testid="depth-profile" data-prefer={props.preferProp ? 'true' : 'false'} />
    },
}))

vi.mock('../MicroStats', () => ({
    MicroStats: (props: any) => {
        microSpy(props)
        return <div data-testid="micro-stats" data-prefer={props.preferProp ? 'true' : 'false'} />
    },
}))

import { LeftPanel } from '../LeftPanel'

afterEach(() => {
    cleanup()
    wallSpy.mockReset()
    depthSpy.mockReset()
    microSpy.mockReset()
    useDashboardStore.setState({ payload: null } as any)
})

function seedPayload() {
    useDashboardStore.setState({
        payload: {
            type: 'dashboard_update',
            timestamp: '2026-03-11T14:45:00Z',
            spot: 560.2,
            agent_g: {
                agent: 'agent_g',
                signal: 'NEUTRAL',
                as_of: '2026-03-11T14:45:00Z',
                data: {
                    gamma_walls: { call_wall: 565, put_wall: 555 },
                    gamma_flip_level: 558,
                    ui_state: {
                        wall_migration: [],
                        depth_profile: [],
                        macro_volume_map: {},
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
    })
}

describe('LeftPanel mode switch', () => {
    it('enables prop-priority contracts in stable mode', () => {
        seedPayload()
        render(<LeftPanel mode="stable" />)

        expect(screen.getByTestId('wall-migration')).toHaveAttribute('data-prefer', 'true')
        expect(screen.getByTestId('depth-profile')).toHaveAttribute('data-prefer', 'true')
        expect(screen.getByTestId('micro-stats')).toHaveAttribute('data-prefer', 'true')
        expect(depthSpy).toHaveBeenCalled()
        expect(depthSpy.mock.calls[0][0].gammaWalls).toEqual({ call_wall: 565, put_wall: 555 })
    })

    it('keeps default selector path in v2 mode', () => {
        seedPayload()
        render(<LeftPanel mode="v2" />)

        expect(screen.getByTestId('wall-migration')).toHaveAttribute('data-prefer', 'false')
        expect(screen.getByTestId('depth-profile')).toHaveAttribute('data-prefer', 'false')
        expect(screen.getByTestId('micro-stats')).toHaveAttribute('data-prefer', 'false')
    })
})

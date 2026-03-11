import { describe, expect, it } from 'vitest'
import type { DashboardPayload } from '../../../types/dashboard'
import { deriveLeftPanelContracts } from '../leftPanelModel'

describe('leftPanelModel', () => {
    it('derives left contracts from payload with finite normalization', () => {
        const payload = {
            type: 'dashboard_update',
            timestamp: '2026-03-11T14:40:00Z',
            spot: 560.25,
            agent_g: {
                agent: 'agent_g',
                signal: 'NEUTRAL',
                as_of: '2026-03-11T14:40:00Z',
                data: {
                    gamma_walls: { call_wall: 565, put_wall: 555 },
                    gamma_flip_level: 558,
                    ui_state: {
                        wall_migration: [
                            { type_label: 'C', current: 565, state: 'REINFORCED', h1: 564, h2: 563 },
                        ],
                        depth_profile: [
                            { strike: 560, put_pct: 0.3, call_pct: 0.5, is_spot: 1, is_flip: 0, is_dominant_put: 0, is_dominant_call: 1 },
                        ],
                        macro_volume_map: { '560': 10, '565': '20' },
                        micro_stats: {
                            net_gex: { label: 'GEX +88M', badge: 'badge-red' },
                            wall_dyn: { label: 'RETREAT ↑', badge: 'badge-red' },
                            vanna: { label: 'NORMAL', badge: 'badge-neutral' },
                            momentum: { label: 'BULLISH', badge: 'badge-red' },
                        },
                    },
                },
            },
        } as unknown as DashboardPayload

        const out = deriveLeftPanelContracts(payload)

        expect(out.spot).toBe(560.25)
        expect(out.gammaWalls?.call_wall).toBe(565)
        expect(out.flipLevel).toBe(558)
        expect(out.wallMigrationRows).toHaveLength(1)
        expect(out.depthProfileRows[0].is_spot).toBe(true)
        expect(out.macroVolumeMap['565']).toBe(20)
        expect(out.microStats?.net_gex.label).toBe('GEX +88M')
    })

    it('returns safe defaults when payload is null', () => {
        const out = deriveLeftPanelContracts(null)
        expect(out.spot).toBeNull()
        expect(out.gammaWalls).toBeNull()
        expect(out.flipLevel).toBeNull()
        expect(out.wallMigrationRows).toEqual([])
        expect(out.depthProfileRows).toEqual([])
        expect(out.macroVolumeMap).toEqual({})
        expect(out.microStats).toBeNull()
    })
})

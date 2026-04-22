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

    it('prefers canonical wall_migration contract and preserves lights/history', () => {
        const payload = {
            type: 'dashboard_update',
            timestamp: '2026-03-11T14:42:00Z',
            spot: 560.5,
            agent_g: {
                agent: 'agent_g',
                signal: 'NEUTRAL',
                as_of: '2026-03-11T14:42:00Z',
                data: {
                    gamma_walls: { call_wall: 566, put_wall: 554 },
                    gamma_flip_level: 559,
                    ui_state: {
                        wall_migration: [
                            {
                                label: 'CALL WALL',
                                strike: 566,
                                state: 'REINFORCED',
                                history: [564, 565, 566],
                                lights: { wall_dyn_badge: 'SIEGE' },
                            },
                        ],
                        depth_profile: [
                            { strike: 560, put_pct: 0.35, call_pct: 0.45, is_spot: true, is_flip: false, is_dominant_put: false, is_dominant_call: true },
                        ],
                        macro_volume_map: {},
                        micro_stats: {
                            net_gex: { label: 'GEX +90M', badge: 'badge-red' },
                            wall_dyn: { label: 'SIEGE', badge: 'badge-red' },
                            vanna: { label: 'NORMAL', badge: 'badge-neutral' },
                            momentum: { label: 'BULLISH', badge: 'badge-red' },
                        },
                    },
                },
            },
        } as unknown as DashboardPayload

        const out = deriveLeftPanelContracts(payload)

        expect(out.wallMigrationRows).toHaveLength(1)
        expect(out.wallMigrationRows[0].label).toBe('CALL WALL')
        expect(out.wallMigrationRows[0].strike).toBe(566)
        expect(out.wallMigrationRows[0].history).toEqual([564, 565, 566])
        expect(out.wallMigrationRows[0].lights?.wall_dyn_badge).toBe('SIEGE')
        expect(out.depthProfileRows[0].call_pct).toBe(0.45)
        expect(out.depthProfileRows[0].put_pct).toBe(0.35)
    })

    it('uses gamma_walls as canonical strike source for wall rows', () => {
        const payload = {
            type: 'dashboard_update',
            timestamp: '2026-03-11T14:45:00Z',
            spot: 560.5,
            agent_g: {
                agent: 'agent_g',
                signal: 'NEUTRAL',
                as_of: '2026-03-11T14:45:00Z',
                data: {
                    gamma_walls: { call_wall: 570, put_wall: 550 },
                    gamma_flip_level: 559,
                    ui_state: {
                        wall_migration: [
                            { label: 'CALL WALL', strike: 566, state: 'REINFORCED', history: [564, 565, 566] },
                            { label: 'PUT WALL', strike: 554, state: 'STABLE', history: [552, 553, 554] },
                        ],
                        depth_profile: [],
                        macro_volume_map: {},
                        micro_stats: {
                            net_gex: { label: 'GEX +90M', badge: 'badge-red' },
                            wall_dyn: { label: 'SIEGE', badge: 'badge-red' },
                            vanna: { label: 'NORMAL', badge: 'badge-neutral' },
                            momentum: { label: 'BULLISH', badge: 'badge-red' },
                        },
                    },
                },
            },
        } as unknown as DashboardPayload

        const out = deriveLeftPanelContracts(payload)

        expect(out.wallMigrationRows).toHaveLength(2)
        expect(out.wallMigrationRows[0].strike).toBe(570)
        expect(out.wallMigrationRows[1].strike).toBe(550)
        expect(out.wallMigrationRows[0].history).toEqual([564, 565, 566])
        expect(out.wallMigrationRows[1].history).toEqual([552, 553, 554])
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

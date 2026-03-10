import { describe, expect, it } from 'vitest'
import { buildDebugOverlayModel } from '../debugOverlayModel'
import type { DashboardPayload } from '../../types/dashboard'

function basePayload(): DashboardPayload {
    return {
        type: 'dashboard_update',
        timestamp: '2026-03-06T14:31:00Z',
        spot: 560.12,
        agent_g: null,
        rust_active: false,
        shm_stats: null,
    }
}

describe('buildDebugOverlayModel', () => {
    it('keeps valid zero raw fields visible', () => {
        const payload = basePayload()
        payload.agent_g = {
            agent: 'agent_g',
            signal: 'NEUTRAL',
            as_of: payload.timestamp,
            data: {
                agent_a: { signal: 'NEUTRAL', data: { spot: null, vwap: null, vwap_std: 0, slope: 0 } },
                agent_b: {
                    signal: 'NEUTRAL',
                    data: {
                        net_gex: null,
                        spy_atm_iv: null,
                        gamma_walls: { call_wall: null, put_wall: null },
                        gamma_flip: false,
                        gamma_flip_level: null,
                        per_strike_gex: [],
                        micro_structure: null,
                        iv_confidence: 0,
                        wall_confidence: 0,
                        vanna_confidence: 0,
                        mtf_consensus: { timeframes: {} },
                    },
                },
                net_gex: null,
                gex_regime: 'NEUTRAL',
                gamma_walls: { call_wall: null, put_wall: null },
                gamma_flip_level: null,
                spy_atm_iv: null,
                trap_state: 'NONE',
                fused_signal: {
                    direction: 'NEUTRAL',
                    confidence: 0,
                    weights: { iv: 0, wall: 0, vanna: 0, mtf: 0 },
                    regime: 'NEUTRAL',
                    iv_regime: 'NORMAL',
                    gex_intensity: 'LOW',
                    explanation: '',
                    components: {},
                    raw_vpin: 0,
                    raw_bbo_imb: 0,
                    raw_vol_accel: 0,
                },
                micro_structure: null,
                ui_state: {
                    micro_stats: {
                        net_gex: { label: '-', badge: 'badge-neutral' },
                        wall_dyn: { label: '-', badge: 'badge-neutral' },
                        vanna: { label: '-', badge: 'badge-neutral' },
                        momentum: { label: '-', badge: 'badge-neutral' },
                    },
                    wall_migration: [],
                    depth_profile: [],
                    macro_volume_map: {},
                    atm: null,
                },
            },
        }

        const model = buildDebugOverlayModel(payload, 'connected')
        expect(model.vpin).toBe('0')
        expect(model.bbo).toBe('0')
        expect(model.volAccel).toBe('0')
        expect(model.connStatus).toBe('CONNECTED')
    })

    it('parses shm pointers and computes lag', () => {
        const payload = basePayload()
        payload.rust_active = true
        payload.shm_stats = { status: 'OK', head: '120', tail: 95 }

        const model = buildDebugOverlayModel(payload, 'connected')
        expect(model.shmStatus).toBe('OK')
        expect(model.shmHead).toBe('120')
        expect(model.shmTail).toBe('95')
        expect(model.shmLag).toBe('25')
    })

    it('falls back to DISCONNECTED when shm metadata missing', () => {
        const model = buildDebugOverlayModel(basePayload(), 'disconnected')
        expect(model.shmStatus).toBe('DISCONNECTED')
        expect(model.shmHead).toBe('N/A')
        expect(model.shmTail).toBe('N/A')
        expect(model.shmLag).toBe('N/A')
    })
})

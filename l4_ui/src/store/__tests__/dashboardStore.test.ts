/**
 * Tests: DashboardStore (Phase 1)
 * ─────────────────────────────────
 * 15 assertions covering:
 *   • Initial state correctness
 *   • applyFullUpdate: slice extraction (spot, ivPct, atm)
 *   • applyFullUpdate: sticky-key protection (smartMergeUiState)
 *   • applyMergedPayload: delta merge on top of existing state
 *   • appendAtmHistory: deduplication + ring-buffer cap
 *   • setConnectionStatus
 *   • Named selectors: selectSpot, selectAtm, selectIvPct etc.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useDashboardStore, smartMergeUiState } from '../../store/dashboardStore'
import type { DashboardPayload } from '../../types/dashboard'

// ─────────────────────────────────────────────────────────────────────────────
// Fixture helpers
// ─────────────────────────────────────────────────────────────────────────────

function makePayload(overrides: Partial<DashboardPayload> = {}): DashboardPayload {
    return {
        type: 'dashboard_update',
        timestamp: '2026-01-01T09:30:00Z',
        spot: 560.0,
        agent_g: {
            agent: 'agent_g',
            signal: 'BULLISH',
            as_of: '2026-01-01T09:30:00Z',
            data: {
                agent_a: { signal: 'BULLISH', data: { spot: 560.0, vwap: 558.0, vwap_std: 1.2, slope: 0.3 } },
                agent_b: {
                    signal: 'BULLISH',
                    data: {
                        net_gex: 120.5,
                        spy_atm_iv: 0.185,
                        gamma_walls: { call_wall: 565.0, put_wall: 555.0 },
                        gamma_flip: false,
                        gamma_flip_level: 558.0,
                        per_strike_gex: [],
                        micro_structure: null,
                        iv_confidence: 0.9,
                        wall_confidence: 0.8,
                        vanna_confidence: 0.7,
                        mtf_consensus: { timeframes: {} },
                    },
                },
                net_gex: 120.5,
                gex_regime: 'DAMPING',
                gamma_walls: { call_wall: 565.0, put_wall: 555.0 },
                gamma_flip_level: 558.0,
                spy_atm_iv: 0.185,
                trap_state: 'NONE',
                fused_signal: {
                    direction: 'BULLISH',
                    confidence: 0.82,
                    weights: { iv: 0.3, wall: 0.25, vanna: 0.2, mtf: 0.25 },
                    regime: 'NORMAL',
                    iv_regime: 'NORMAL',
                    gex_intensity: 'HIGH',
                    explanation: 'Test',
                    components: {},
                },
                micro_structure: null,
                ui_state: {
                    micro_stats: {
                        net_gex: { label: 'GEX +120M', badge: 'badge-red' },
                        wall_dyn: { label: 'DAMPING', badge: 'badge-green' },
                        vanna: { label: 'GRIND_STABLE', badge: 'badge-neutral' },
                        momentum: { label: 'BULLISH', badge: 'badge-red' },
                    },
                    wall_migration: [{ type_label: 'CALL', type_bg: '', type_text: '', h1: 565, h2: null, current: 565, dot_color: '', current_border: '', current_bg: '', current_shadow: '', current_text: '' }],
                    depth_profile: [{ strike: 560, put_pct: -0.5, call_pct: 0.5, put_color: '#10b981', call_color: '#ef4444', put_label_color: '', call_label_color: '', spot_tag_classes: '', flip_tag_classes: '', is_dominant_put: false, is_dominant_call: true, is_spot: true, is_flip: false, strike_color: '' }],
                    macro_volume_map: { '560': 12000 },
                    atm: { strike: 560, locked_at: '2026-01-01T09:30:00Z', straddle_pct: 0.022, call_pct: 0.011, put_pct: 0.011, timestamp: '2026-01-01T09:30:00Z' },
                },
            },
        },
        ...overrides,
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('DashboardStore', () => {
    beforeEach(() => {
        // Reset Zustand store between tests by re-applying initial state
        useDashboardStore.setState({
            connectionStatus: 'connecting',
            payload: null,
            spot: null,
            ivPct: null,
            atm: null,
            atmHistory: [],
            version: 0,
        })
    })

    // ── Initial state ──────────────────────────────────────────────────────────

    it('starts with null payload and connecting status', () => {
        const s = useDashboardStore.getState()
        expect(s.payload).toBeNull()
        expect(s.connectionStatus).toBe('connecting')
        expect(s.spot).toBeNull()
        expect(s.version).toBe(0)
    })

    // ── setConnectionStatus ─────────────────────────────────────────────────────

    it('setConnectionStatus updates connectionStatus', () => {
        useDashboardStore.getState().setConnectionStatus('connected')
        expect(useDashboardStore.getState().connectionStatus).toBe('connected')
    })

    // ── applyFullUpdate ─────────────────────────────────────────────────────────

    it('applyFullUpdate extracts spot correctly', () => {
        useDashboardStore.getState().applyFullUpdate(makePayload({ spot: 562.5 }))
        expect(useDashboardStore.getState().spot).toBe(562.5)
    })

    it('applyFullUpdate extracts ivPct from agent_g.data.spy_atm_iv', () => {
        useDashboardStore.getState().applyFullUpdate(makePayload())
        expect(useDashboardStore.getState().ivPct).toBe(0.185)
    })

    it('applyFullUpdate extracts atm from ui_state.atm', () => {
        useDashboardStore.getState().applyFullUpdate(makePayload())
        const atm = useDashboardStore.getState().atm
        expect(atm).not.toBeNull()
        expect(atm!.strike).toBe(560)
        expect(atm!.straddle_pct).toBe(0.022)
    })

    it('applyFullUpdate increments version', () => {
        useDashboardStore.getState().applyFullUpdate(makePayload())
        expect(useDashboardStore.getState().version).toBe(1)
        useDashboardStore.getState().applyFullUpdate(makePayload())
        expect(useDashboardStore.getState().version).toBe(2)
    })

    it('applyFullUpdate populates atmHistory on first tick', () => {
        useDashboardStore.getState().applyFullUpdate(makePayload())
        expect(useDashboardStore.getState().atmHistory).toHaveLength(1)
    })

    // ── ATM history deduplication ───────────────────────────────────────────────

    it('applyFullUpdate deduplicates ATM ticks by timestamp', () => {
        const p = makePayload()
        useDashboardStore.getState().applyFullUpdate(p)
        useDashboardStore.getState().applyFullUpdate(p) // same timestamp
        expect(useDashboardStore.getState().atmHistory).toHaveLength(1)
    })

    it('appendAtmHistory accumulates unique ticks and deduplicates', () => {
        const tick1 = { strike: 560, locked_at: null, straddle_pct: 0.02, call_pct: 0.01, put_pct: 0.01, timestamp: 'T1' }
        const tick2 = { ...tick1, timestamp: 'T2' }
        useDashboardStore.getState().appendAtmHistory(tick1)
        useDashboardStore.getState().appendAtmHistory(tick2)
        useDashboardStore.getState().appendAtmHistory(tick1) // dup
        expect(useDashboardStore.getState().atmHistory).toHaveLength(2)
    })

    // ── Sticky-key protection ───────────────────────────────────────────────────

    it('applyFullUpdate sticky-merge keeps wall_migration when new is empty', () => {
        const first = makePayload()
        useDashboardStore.getState().applyFullUpdate(first)
        const wallMigration = useDashboardStore.getState().payload!.agent_g!.data.ui_state.wall_migration
        expect(wallMigration).toHaveLength(1)

        // Second update has empty wall_migration
        const second = makePayload()
            ; (second.agent_g!.data.ui_state as any).wall_migration = []
        useDashboardStore.getState().applyFullUpdate(second)

        // Should retain previous data
        const retained = useDashboardStore.getState().payload!.agent_g!.data.ui_state.wall_migration
        expect(retained).toHaveLength(1)
    })

    it('does not carry sticky ui_state across ET trade-date boundary', () => {
        const first = makePayload({
            timestamp: '2026-01-01T20:59:00Z',
            data_timestamp: '2026-01-01T20:59:00Z',
        })
        useDashboardStore.getState().applyFullUpdate(first)
        expect(useDashboardStore.getState().payload!.agent_g!.data.ui_state.wall_migration).toHaveLength(1)

        const second = makePayload({
            timestamp: '2026-01-02T14:31:00Z',
            data_timestamp: '2026-01-02T14:31:00Z',
        })
        ;(second.agent_g!.data.ui_state as any).wall_migration = []
        useDashboardStore.getState().applyFullUpdate(second)

        const migrated = useDashboardStore.getState().payload!.agent_g!.data.ui_state.wall_migration
        expect(migrated).toHaveLength(0)
    })

    it('keeps atmHistory scoped to current ET trade-date', () => {
        const day1 = makePayload({
            timestamp: '2026-01-01T20:59:00Z',
            data_timestamp: '2026-01-01T20:59:00Z',
            atm: {
                strike: 560,
                locked_at: '2026-01-01T20:59:00Z',
                straddle_pct: 0.02,
                call_pct: 0.01,
                put_pct: 0.01,
                timestamp: '2026-01-01T20:59:00Z',
            },
        })
        useDashboardStore.getState().applyFullUpdate(day1)
        expect(useDashboardStore.getState().atmHistory).toHaveLength(1)

        const day2 = makePayload({
            timestamp: '2026-01-02T14:31:00Z',
            data_timestamp: '2026-01-02T14:31:00Z',
            atm: {
                strike: 561,
                locked_at: '2026-01-02T14:31:00Z',
                straddle_pct: 0.03,
                call_pct: 0.015,
                put_pct: 0.015,
                timestamp: '2026-01-02T14:31:00Z',
            },
        })
        useDashboardStore.getState().applyFullUpdate(day2)

        const history = useDashboardStore.getState().atmHistory
        expect(history).toHaveLength(1)
        expect(history[0].timestamp).toBe('2026-01-02T14:31:00Z')
    })

    // ── applyMergedPayload ─────────────────────────────────────────────────────

    it('applyMergedPayload updates spot and version', () => {
        useDashboardStore.getState().applyFullUpdate(makePayload())
        const delta = makePayload({ spot: 563.0 })
        useDashboardStore.getState().applyMergedPayload(delta)
        expect(useDashboardStore.getState().spot).toBe(563.0)
        expect(useDashboardStore.getState().version).toBe(2)
    })
})

// ─────────────────────────────────────────────────────────────────────────────
// smartMergeUiState (unit tested directly)
// ─────────────────────────────────────────────────────────────────────────────

describe('smartMergeUiState', () => {
    it('preserves sticky keys when new value is null', () => {
        const prev = { wall_migration: [{ strike: 560 }], micro_stats: {} }
        const next = { wall_migration: null, micro_stats: { net_gex: {} } }
        const merged = smartMergeUiState(prev, next)
        expect(merged.wall_migration).toEqual([{ strike: 560 }])
        expect(merged.micro_stats).toEqual({ net_gex: {} }) // non-sticky = overwrite
    })

    it('preserves sticky keys when new value is empty array', () => {
        const prev = { depth_profile: [{ strike: 560 }] }
        const next = { depth_profile: [] }
        expect(smartMergeUiState(prev, next).depth_profile).toEqual([{ strike: 560 }])
    })

    it('allows non-sticky key overwrite with empty value', () => {
        const prev = { micro_stats: { net_gex: { label: 'OLD' } } }
        const next = { micro_stats: {} }
        expect(smartMergeUiState(prev, next).micro_stats).toEqual({})
    })

    it('allows sticky key update when new value is non-empty', () => {
        const prev = { wall_migration: [{ strike: 555 }] }
        const next = { wall_migration: [{ strike: 560 }, { strike: 565 }] }
        expect(smartMergeUiState(prev, next).wall_migration).toHaveLength(2)
    })
})

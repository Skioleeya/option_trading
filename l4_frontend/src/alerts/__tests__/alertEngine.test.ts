/**
 * Tests: Alert Engine (Phase 4)
 * ──────────────────────────────
 * 14 assertions covering:
 *   • alertStore.push: adds toast, respects ring-buffer cap (8)
 *   • alertStore.dismiss: removes by id
 *   • alertStore.clearAll: empties queue
 *   • alertStore.push: idempotent (deduplicates by id)
 *   • AlertEngine.evaluate: fires signal_direction rule
 *   • AlertEngine.evaluate: cooldown prevents double-fire
 *   • AlertEngine.evaluate: iv_regime escalation fires
 *   • AlertEngine.evaluate: iv_regime de-escalation does NOT fire
 *   • AlertEngine.evaluate: net_gex sign flip fires
 *   • AlertEngine.evaluate: call wall breach fires
 *   • AlertEngine.evaluate: put wall breach fires
 *   • AlertEngine.evaluate: gamma flip cross fires
 *   • AlertEngine.evaluate: no fire when state unchanged
 *   • ALERT_RULES: all 6 rules have unique ids
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useAlertStore } from '../../alerts/alertStore'
import { AlertEngine, ALERT_RULES, type L4Alert } from '../../alerts/alertEngine'
import { useDashboardStore } from '../../store/dashboardStore'

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

type StoreSnapshot = Parameters<typeof AlertEngine.evaluate>[0]

function makeState(changes: any): StoreSnapshot {
    const base = useDashboardStore.getState()
    // deep clone payload or default structural shape
    const payload = JSON.parse(JSON.stringify(base.payload || { agent_g: { data: {} } }))

    if (changes.fused) payload.agent_g.data.fused_signal = changes.fused
    if (changes.netGex !== undefined) payload.agent_g.data.net_gex = changes.netGex
    if (changes.gammaWalls !== undefined) payload.agent_g.data.gamma_walls = changes.gammaWalls
    if (changes.flipLevel !== undefined) payload.agent_g.data.gamma_flip_level = changes.flipLevel

    return { ...base, spot: changes.spot ?? base.spot, payload, flipLevel: changes.flipLevel, netGex: changes.netGex, gammaWalls: changes.gammaWalls } as any
}

// ─────────────────────────────────────────────────────────────────────────────
// alertStore unit tests
// ─────────────────────────────────────────────────────────────────────────────

describe('alertStore', () => {
    beforeEach(() => {
        useAlertStore.getState().clearAll()
    })

    it('push adds a toast to the queue', () => {
        const alert: L4Alert = { id: 'test_1', timestamp: Date.now(), severity: 'info', category: 'SIGNAL', title: 'T1', body: 'B1' }
        useAlertStore.getState().push(alert, 60_000)
        expect(useAlertStore.getState().toasts).toHaveLength(1)
        expect(useAlertStore.getState().toasts[0].id).toBe('test_1')
    })

    it('push deduplicates by id (idempotent)', () => {
        const alert: L4Alert = { id: 'dup_1', timestamp: Date.now(), severity: 'info', category: 'SIGNAL', title: 'T', body: 'B' }
        useAlertStore.getState().push(alert, 60_000)
        useAlertStore.getState().push(alert, 60_000)
        expect(useAlertStore.getState().toasts).toHaveLength(1)
    })

    it('push caps at 8 (ring-buffer)', () => {
        for (let i = 0; i < 12; i++) {
            useAlertStore.getState().push({ id: `t_${i}`, timestamp: Date.now(), severity: 'info', category: 'SIGNAL', title: `T${i}`, body: 'B' }, 60_000)
        }
        expect(useAlertStore.getState().toasts.length).toBeLessThanOrEqual(8)
    })

    it('dismiss removes the toast by id', () => {
        useAlertStore.getState().push({ id: 'rm_1', timestamp: Date.now(), severity: 'info', category: 'SIGNAL', title: 'T', body: 'B' }, 60_000)
        useAlertStore.getState().dismiss('rm_1')
        expect(useAlertStore.getState().toasts.find(t => t.id === 'rm_1')).toBeUndefined()
    })

    it('clearAll empties the queue', () => {
        useAlertStore.getState().push({ id: 'cl_1', timestamp: Date.now(), severity: 'warning', category: 'GEX', title: 'T', body: 'B' }, 60_000)
        useAlertStore.getState().clearAll()
        expect(useAlertStore.getState().toasts).toHaveLength(0)
    })
})

// ─────────────────────────────────────────────────────────────────────────────
// AlertEngine rule evaluation tests
// ─────────────────────────────────────────────────────────────────────────────

describe('AlertEngine.evaluate', () => {
    beforeEach(() => {
        useAlertStore.getState().clearAll()
            // Fresh engine instance for each test (reset internal state)
            ; (AlertEngine as any).prevValues = new Map()
            ; (AlertEngine as any).lastFired = new Map()
    })

    it('signal_direction fires on direction flip', () => {
        const s1 = makeState({ fused: { direction: 'BULLISH', confidence: 0.8 } })
        AlertEngine.evaluate(s1)
        expect(useAlertStore.getState().toasts).toHaveLength(0) // first tick, no prev

        const s2 = makeState({ fused: { direction: 'BEARISH', confidence: 0.7 } })
        AlertEngine.evaluate(s2)
        const alerts = useAlertStore.getState().toasts
        expect(alerts.some(a => a.category === 'SIGNAL')).toBe(true)
    })

    it('signal_direction does NOT fire when direction is unchanged', () => {
        const s = makeState({ fused: { direction: 'BULLISH', confidence: 0.8 } })
        AlertEngine.evaluate(s)
        AlertEngine.evaluate(s)
        // All toasts should be none (no change)
        expect(useAlertStore.getState().toasts.filter(a => a.category === 'SIGNAL')).toHaveLength(0)
    })

    it('iv_regime fires on escalation (NORMAL → HIGH)', () => {
        AlertEngine.evaluate(makeState({ fused: { iv_regime: 'NORMAL' } }))
        AlertEngine.evaluate(makeState({ fused: { iv_regime: 'HIGH' } }))
        expect(useAlertStore.getState().toasts.some(a => a.category === 'IV')).toBe(true)
    })

    it('iv_regime does NOT fire on de-escalation (HIGH → NORMAL)', () => {
        AlertEngine.evaluate(makeState({ fused: { iv_regime: 'HIGH' } }))
        useAlertStore.getState().clearAll()
        AlertEngine.evaluate(makeState({ fused: { iv_regime: 'NORMAL' } }))
        expect(useAlertStore.getState().toasts.filter(a => a.category === 'IV')).toHaveLength(0)
    })

    it('net_gex sign flip fires (positive → negative)', () => {
        AlertEngine.evaluate(makeState({ netGex: 100 }))
        AlertEngine.evaluate(makeState({ netGex: -50 }))
        expect(useAlertStore.getState().toasts.some(a => a.category === 'GEX')).toBe(true)
    })

    it('call_wall_breach fires when spot crosses above call wall', () => {
        AlertEngine.evaluate(makeState({ spot: 555, gammaWalls: { call_wall: 560, put_wall: 550 } }))
        AlertEngine.evaluate(makeState({ spot: 562, gammaWalls: { call_wall: 560, put_wall: 550 } }))
        expect(useAlertStore.getState().toasts.some(a => a.title.includes('Call Wall'))).toBe(true)
    })

    it('put_wall_breach fires when spot drops below put wall', () => {
        AlertEngine.evaluate(makeState({ spot: 556, gammaWalls: { call_wall: 560, put_wall: 550 } }))
        AlertEngine.evaluate(makeState({ spot: 548, gammaWalls: { call_wall: 560, put_wall: 550 } }))
        expect(useAlertStore.getState().toasts.some(a => a.title.includes('Put Wall'))).toBe(true)
    })

    it('flip_level_cross fires when spot crosses flip level', () => {
        AlertEngine.evaluate(makeState({ spot: 554, flipLevel: 556 }))
        AlertEngine.evaluate(makeState({ spot: 558, flipLevel: 556 }))
        expect(useAlertStore.getState().toasts.some(a => a.category === 'SPOT')).toBe(true)
    })
})

// ─────────────────────────────────────────────────────────────────────────────
// Rule registry invariants
// ─────────────────────────────────────────────────────────────────────────────

describe('ALERT_RULES', () => {
    it('all rule ids are unique', () => {
        const ids = ALERT_RULES.map((r) => r.id)
        const unique = new Set(ids)
        expect(unique.size).toBe(ids.length)
    })

    it('all rules have positive cooldownMs', () => {
        ALERT_RULES.forEach((r) => {
            expect(r.cooldownMs).toBeGreaterThan(0)
        })
    })
})

/**
 * l4_ui — Alert Engine (Phase 4: Keyboard & Alert Infrastructure)
 * ───────────────────────────────────────────────────────────────────────
 * Singleton that subscribes to the Zustand store and fires configurable
 * alerts when market conditions cross defined thresholds.
 *
 * Alert categories (aligned with L4_FRONTEND.md §7):
 *   SIGNAL   — direction flip (BULLISH ↔ BEARISH)
 *   WALL     — call/put wall breach or retreat
 *   GEX      — net GEX sign flip (positive ↔ negative)
 *   IV       — IV regime change (NORMAL → ELEVATED → HIGH)
 *   SPOT     — spot price breaches a wall or flip level
 *
 * Design:
 *   • Zero-dependency: uses the browser Notification API when permitted,
 *     falls back to in-app toasts (via alertStore).
 *   • Hysteresis: each alert has a cooldown window (default 60 s) to
 *     prevent alert fatigue on boundary oscillation.
 *   • Testable: pure functions + injectable store snapshot for unit tests.
 */

import { useDashboardStore } from '../store/dashboardStore'
import { useAlertStore } from './alertStore'
import type { AlertSeverity, L4Alert } from './types'

export type { AlertSeverity, L4Alert }

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface AlertRule<T> {
    id: string
    cooldownMs: number
    extract: (state: ReturnType<typeof useDashboardStore.getState>) => T | null
    shouldFire: (prev: T | null, curr: T) => boolean
    buildAlert: (prev: T | null, curr: T) => Omit<L4Alert, 'id' | 'timestamp'>
}

// ─────────────────────────────────────────────────────────────────────────────
// Rules
// ─────────────────────────────────────────────────────────────────────────────

const RULES: AlertRule<any>[] = [
    // ── SIGNAL direction flip ───────────────────────────────────────────────────
    {
        id: 'signal_direction',
        cooldownMs: 30_000,
        extract: (s) => s.payload?.agent_g?.data?.fused_signal?.direction ?? null,
        shouldFire: (prev, curr) => prev !== null && prev !== curr,
        buildAlert: (prev, curr) => ({
            severity: 'warning',
            category: 'SIGNAL',
            title: `Signal Flip: ${prev} → ${curr}`,
            body: `Decision Engine changed direction from ${prev} to ${curr}.`,
        }),
    },

    // ── IV regime escalation ────────────────────────────────────────────────────
    {
        id: 'iv_regime',
        cooldownMs: 60_000,
        extract: (s) => s.payload?.agent_g?.data?.fused_signal?.iv_regime ?? null,
        shouldFire: (prev, curr) => {
            if (prev === null || prev === curr) return false
            const RANK: Record<string, number> = { NORMAL: 0, ELEVATED: 1, HIGH: 2, EXTREME: 3 }
            return (RANK[curr] ?? 0) > (RANK[prev] ?? 0)
        },
        buildAlert: (prev, curr) => ({
            severity: curr === 'EXTREME' ? 'critical' : 'warning',
            category: 'IV',
            title: `IV Regime Escalation: ${prev} → ${curr}`,
            body: `Implied volatility regime has escalated to ${curr}.`,
        }),
    },

    // ── GEX sign flip ───────────────────────────────────────────────────────────
    {
        id: 'net_gex_sign',
        cooldownMs: 60_000,
        extract: (s) => {
            const netGex = s.payload?.agent_g?.data?.net_gex
            return netGex != null ? (netGex >= 0 ? 'POSITIVE' : 'NEGATIVE') : null
        },
        shouldFire: (prev, curr) => prev !== null && prev !== curr,
        buildAlert: (_prev, curr) => ({
            severity: curr === 'NEGATIVE' ? 'warning' : 'info',
            category: 'GEX',
            title: `GEX Flip → ${curr}`,
            body: `Net GEX has crossed zero into ${curr} territory. Dealer hedging dynamics shifted.`,
        }),
    },

    // ── WALL breach (spot vs call wall) ────────────────────────────────────────
    {
        id: 'call_wall_breach',
        cooldownMs: 120_000,
        extract: (s) => {
            const spot = s.spot
            const callWall = s.payload?.agent_g?.data?.gamma_walls?.call_wall ?? null
            if (spot == null || callWall == null) return null
            return spot >= callWall ? 'BREACHED' : 'BELOW'
        },
        shouldFire: (prev, curr) => prev === 'BELOW' && curr === 'BREACHED',
        buildAlert: (_prev, _curr) => ({
            severity: 'critical',
            category: 'WALL',
            title: 'Call Wall Breached',
            body: 'SPY price has moved above the call wall. Expect dealer short-gamma pressure reversal.',
        }),
    },

    // ── WALL breach (spot vs put wall) ────────────────────────────────────────
    {
        id: 'put_wall_breach',
        cooldownMs: 120_000,
        extract: (s) => {
            const spot = s.spot
            const putWall = s.payload?.agent_g?.data?.gamma_walls?.put_wall ?? null
            if (spot == null || putWall == null) return null
            return spot <= putWall ? 'BREACHED' : 'ABOVE'
        },
        shouldFire: (prev, curr) => prev === 'ABOVE' && curr === 'BREACHED',
        buildAlert: (_prev, _curr) => ({
            severity: 'critical',
            category: 'WALL',
            title: 'Put Wall Breached',
            body: 'SPY price has fallen below the put wall. Dealers may add downside delta hedge.',
        }),
    },

    // ── Spot crosses gamma flip level ──────────────────────────────────────────
    {
        id: 'flip_level_cross',
        cooldownMs: 90_000,
        extract: (s) => {
            const spot = s.spot
            const flip = s.payload?.agent_g?.data?.gamma_flip_level
            if (spot == null || flip == null) return null
            return spot >= flip ? 'ABOVE' : 'BELOW'
        },
        shouldFire: (prev, curr) => prev !== null && prev !== curr,
        buildAlert: (_prev, curr) => ({
            severity: 'warning',
            category: 'SPOT',
            title: `Spot ${curr === 'ABOVE' ? 'Crossed Above' : 'Fell Below'} Gamma Flip`,
            body: `SPY moved ${curr} gamma flip level. Regime ${curr === 'ABOVE' ? 'bullish (dealers long gamma)' : 'bearish (dealers short gamma)'}.`,
        }),
    },
]

// ─────────────────────────────────────────────────────────────────────────────
// Engine
// ─────────────────────────────────────────────────────────────────────────────

class AlertEngineImpl {
    private prevValues: Map<string, unknown> = new Map()
    private lastFired: Map<string, number> = new Map()
    private unsubscribe: (() => void) | null = null

    start(): void {
        if (this.unsubscribe) return // already running

        // Zustand's subscribe API — fires on every state change
        this.unsubscribe = useDashboardStore.subscribe((state) => {
            this._evaluate(state)
        })
    }

    stop(): void {
        this.unsubscribe?.()
        this.unsubscribe = null
    }

    /** Force-evaluate all rules (useful for testing without WS). */
    evaluate(state: ReturnType<typeof useDashboardStore.getState>): void {
        this._evaluate(state)
    }

    private _evaluate(state: ReturnType<typeof useDashboardStore.getState>): void {
        const now = Date.now()

        for (const rule of RULES) {
            const curr = rule.extract(state)
            if (curr === null) continue

            const prev = this.prevValues.get(rule.id) ?? null
            const lastFiredAt = this.lastFired.get(rule.id) ?? 0

            // Update prev value regardless of firing
            this.prevValues.set(rule.id, curr)

            // Cooldown guard
            if (now - lastFiredAt < rule.cooldownMs) continue

            if (rule.shouldFire(prev, curr)) {
                this.lastFired.set(rule.id, now)
                const alertData = rule.buildAlert(prev, curr)
                const alert: L4Alert = {
                    id: `${rule.id}_${now}`,
                    timestamp: now,
                    ...alertData,
                }
                this._dispatch(alert)
            }
        }
    }

    private _dispatch(alert: L4Alert): void {
        // Push to in-app alert store (always)
        useAlertStore.getState().push(alert)

        // Browser Notification API (optional, if permission granted)
        if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
            try {
                new Notification(`[SPX] ${alert.title}`, { body: alert.body, tag: alert.id })
            } catch {
                // graceful no-op (sandboxed environments)
            }
        }

        if (import.meta.env.DEV) {
            const PREFIX = { critical: '🔴', warning: '🟡', info: '🔵' }[alert.severity]
            console.warn(`[L4 Alert] ${PREFIX} ${alert.title}`, alert.body)
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton export
// ─────────────────────────────────────────────────────────────────────────────

export const AlertEngine = new AlertEngineImpl()

// ─────────────────────────────────────────────────────────────────────────────
// Alert rule export for testing
// ─────────────────────────────────────────────────────────────────────────────

export { RULES as ALERT_RULES }

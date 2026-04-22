/**
 * Alert engine — subscribes only to the fields required by alert rules.
 */
import { shallow } from 'zustand/shallow'
import { useDashboardStore } from '../store/dashboardStore'
import { useAlertStore } from './alertStore'
import type { AlertSeverity, L4Alert } from './types'

export type { AlertSeverity, L4Alert }

type AlertSnapshot = {
    direction: string | null
    ivRegime: string | null
    netGexSign: 'POSITIVE' | 'NEGATIVE' | null
    callWallState: 'BREACHED' | 'BELOW' | null
    putWallState: 'BREACHED' | 'ABOVE' | null
    flipState: 'ABOVE' | 'BELOW' | null
}

interface AlertRule<T> {
    id: string
    cooldownMs: number
    extract: (state: AlertSnapshot) => T | null
    shouldFire: (prev: T | null, curr: T) => boolean
    buildAlert: (prev: T | null, curr: T) => Omit<L4Alert, 'id' | 'timestamp'>
}

function selectAlertSnapshot(state: ReturnType<typeof useDashboardStore.getState>): AlertSnapshot {
    const spot = state.spot
    const data = state.payload?.agent_g?.data
    const callWall = data?.gamma_walls?.call_wall ?? null
    const putWall = data?.gamma_walls?.put_wall ?? null
    const flip = data?.gamma_flip_level ?? null
    return {
        direction: data?.fused_signal?.direction ?? null,
        ivRegime: data?.fused_signal?.iv_regime ?? null,
        netGexSign: data?.net_gex == null ? null : (data.net_gex >= 0 ? 'POSITIVE' : 'NEGATIVE'),
        callWallState: spot == null || callWall == null ? null : (spot >= callWall ? 'BREACHED' : 'BELOW'),
        putWallState: spot == null || putWall == null ? null : (spot <= putWall ? 'BREACHED' : 'ABOVE'),
        flipState: spot == null || flip == null ? null : (spot >= flip ? 'ABOVE' : 'BELOW'),
    }
}

const RULES: AlertRule<any>[] = [
    {
        id: 'signal_direction',
        cooldownMs: 30_000,
        extract: (s) => s.direction,
        shouldFire: (prev, curr) => prev !== null && prev !== curr,
        buildAlert: (prev, curr) => ({
            severity: 'warning',
            category: 'SIGNAL',
            title: `Signal Flip: ${prev} → ${curr}`,
            body: `Decision Engine changed direction from ${prev} to ${curr}.`,
        }),
    },
    {
        id: 'iv_regime',
        cooldownMs: 60_000,
        extract: (s) => s.ivRegime,
        shouldFire: (prev, curr) => {
            if (prev === null || prev === curr) return false
            const rank: Record<string, number> = { NORMAL: 0, ELEVATED: 1, HIGH: 2, EXTREME: 3 }
            return (rank[curr] ?? 0) > (rank[prev] ?? 0)
        },
        buildAlert: (prev, curr) => ({
            severity: curr === 'EXTREME' ? 'critical' : 'warning',
            category: 'IV',
            title: `IV Regime Escalation: ${prev} → ${curr}`,
            body: `Implied volatility regime has escalated to ${curr}.`,
        }),
    },
    {
        id: 'net_gex_sign',
        cooldownMs: 60_000,
        extract: (s) => s.netGexSign,
        shouldFire: (prev, curr) => prev !== null && prev !== curr,
        buildAlert: (_prev, curr) => ({
            severity: curr === 'NEGATIVE' ? 'warning' : 'info',
            category: 'GEX',
            title: `GEX Flip → ${curr}`,
            body: `Net GEX has crossed zero into ${curr} territory. Dealer hedging dynamics shifted.`,
        }),
    },
    {
        id: 'call_wall_breach',
        cooldownMs: 120_000,
        extract: (s) => s.callWallState,
        shouldFire: (prev, curr) => prev === 'BELOW' && curr === 'BREACHED',
        buildAlert: () => ({
            severity: 'critical',
            category: 'WALL',
            title: 'Call Wall Breached',
            body: 'SPY price has moved above the call wall. Expect dealer short-gamma pressure reversal.',
        }),
    },
    {
        id: 'put_wall_breach',
        cooldownMs: 120_000,
        extract: (s) => s.putWallState,
        shouldFire: (prev, curr) => prev === 'ABOVE' && curr === 'BREACHED',
        buildAlert: () => ({
            severity: 'critical',
            category: 'WALL',
            title: 'Put Wall Breached',
            body: 'SPY price has fallen below the put wall. Dealers may add downside delta hedge.',
        }),
    },
    {
        id: 'flip_level_cross',
        cooldownMs: 90_000,
        extract: (s) => s.flipState,
        shouldFire: (prev, curr) => prev !== null && prev !== curr,
        buildAlert: (_prev, curr) => ({
            severity: 'warning',
            category: 'SPOT',
            title: `Spot ${curr === 'ABOVE' ? 'Crossed Above' : 'Fell Below'} Gamma Flip`,
            body: `SPY moved ${curr} gamma flip level. Regime ${curr === 'ABOVE' ? 'bullish (dealers long gamma)' : 'bearish (dealers short gamma)'}.`,
        }),
    },
]

class AlertEngineImpl {
    private prevValues: Map<string, unknown> = new Map()
    private lastFired: Map<string, number> = new Map()
    private unsubscribe: (() => void) | null = null

    start(): void {
        if (this.unsubscribe) return
        this.unsubscribe = useDashboardStore.subscribe(
            selectAlertSnapshot,
            (state) => this._evaluate(state),
            { equalityFn: shallow },
        )
    }

    stop(): void {
        this.unsubscribe?.()
        this.unsubscribe = null
    }

    evaluate(state: ReturnType<typeof useDashboardStore.getState>): void {
        this._evaluate(selectAlertSnapshot(state))
    }

    private _evaluate(state: AlertSnapshot): void {
        const now = Date.now()
        for (const rule of RULES) {
            const curr = rule.extract(state)
            if (curr === null) continue
            const prev = this.prevValues.get(rule.id) ?? null
            const lastFiredAt = this.lastFired.get(rule.id) ?? 0
            this.prevValues.set(rule.id, curr)
            if (now - lastFiredAt < rule.cooldownMs) continue
            if (!rule.shouldFire(prev, curr)) continue
            this.lastFired.set(rule.id, now)
            const alert: L4Alert = {
                id: `${rule.id}_${now}`,
                timestamp: now,
                ...rule.buildAlert(prev, curr),
            }
            this._dispatch(alert)
        }
    }

    private _dispatch(alert: L4Alert): void {
        useAlertStore.getState().push(alert)
        if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
            try {
                new Notification(`[SPX] ${alert.title}`, { body: alert.body, tag: alert.id })
            } catch {
                // sandbox/browser no-op
            }
        }
        if (import.meta.env.DEV) {
            const prefix = { critical: '🔴', warning: '🟡', info: '🔵' }[alert.severity]
            console.warn(`[L4 Alert] ${prefix} ${alert.title}`, alert.body)
        }
    }
}

export const AlertEngine = new AlertEngineImpl()
export { RULES as ALERT_RULES }

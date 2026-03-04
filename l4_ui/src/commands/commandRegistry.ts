/**
 * l4_ui — Command Registry (Phase 4)
 * ──────────────────────────────────────────
 * Declarative list of all keyboard-accessible commands.
 *
 * Each command has:
 *   id      — unique key
 *   label   — displayed in palette
 *   category — grouping header
 *   shortcut — optional hotkey hint
 *   action  — executed on Enter / click
 *
 * Categories:
 *   NAVIGATE — jump to data zones
 *   TOGGLE   — show/hide overlays
 *   ALERTS   — alert management
 *   DEBUG    — developer utilities (DEV only)
 */

import { useAlertStore } from '../alerts/alertStore'
import { AlertEngine } from '../alerts/alertEngine'
import { useDashboardStore } from '../store/dashboardStore'

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface Command {
    id: string
    label: string
    category: string
    shortcut?: string
    action: () => void
    /** Dynamic label — if provided, this overrides `label` at render time. */
    dynamicLabel?: () => string
}

// ─────────────────────────────────────────────────────────────────────────────
// Registry factory (re-created on palette open to get fresh store values)
// ─────────────────────────────────────────────────────────────────────────────

export function buildCommandRegistry(): Command[] {
    const state = useDashboardStore.getState()
    const gammaWalls = state.payload?.agent_g?.data?.gamma_walls
    const callWall = gammaWalls?.call_wall
    const putWall = gammaWalls?.put_wall
    const flipLevel = state.payload?.agent_g?.data?.gamma_flip_level
    const spot = state.spot

    const commands: Command[] = [
        // ── NAVIGATE ─────────────────────────────────────────────────────────────
        {
            id: 'nav_spot',
            label: `Go to Spot ${spot != null ? spot.toFixed(2) : '—'}`,
            category: 'NAVIGATE',
            shortcut: 'S',
            action: () => {
                // Scroll Depth Profile to spot row (spotRef auto-scrolls via useEffect)
                window.dispatchEvent(new CustomEvent('l4:nav_spot'))
            },
        },
        {
            id: 'nav_call_wall',
            label: `Go to Call Wall ${callWall != null ? callWall.toFixed(0) : '—'}`,
            category: 'NAVIGATE',
            action: () => window.dispatchEvent(new CustomEvent('l4:nav_call_wall')),
        },
        {
            id: 'nav_put_wall',
            label: `Go to Put Wall ${putWall != null ? putWall.toFixed(0) : '—'}`,
            category: 'NAVIGATE',
            action: () => window.dispatchEvent(new CustomEvent('l4:nav_put_wall')),
        },
        {
            id: 'nav_flip',
            label: `Go to Gamma Flip ${flipLevel != null ? flipLevel.toFixed(0) : '—'}`,
            category: 'NAVIGATE',
            action: () => window.dispatchEvent(new CustomEvent('l4:nav_flip')),
        },

        // ── ALERTS ────────────────────────────────────────────────────────────────
        {
            id: 'alert_clear_all',
            label: 'Clear All Alerts',
            category: 'ALERTS',
            shortcut: 'Esc',
            action: () => useAlertStore.getState().clearAll(),
        },
        {
            id: 'alert_test_critical',
            label: 'Test: Fire Critical Alert',
            category: 'ALERTS',
            action: () => {
                useAlertStore.getState().push({
                    id: `test_critical_${Date.now()}`,
                    timestamp: Date.now(),
                    severity: 'critical',
                    category: 'SIGNAL',
                    title: 'Test Critical Alert',
                    body: 'This is a test critical alert fired from the Command Palette.',
                })
            },
        },
        {
            id: 'alert_request_permission',
            label: 'Request Browser Notification Permission',
            category: 'ALERTS',
            action: () => {
                if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
                    Notification.requestPermission()
                }
            },
        },

        // ── DEBUG (dev only) ───────────────────────────────────────────────────────
        ...(import.meta.env.DEV ? [
            {
                id: 'debug_rum_snapshot',
                label: 'Debug: Log RUM Snapshot',
                category: 'DEBUG',
                action: () => {
                    import('../observability/l4_rum').then(({ L4Rum }) => {
                        console.table(L4Rum.snapshot())
                    })
                },
            },
            {
                id: 'debug_store_state',
                label: 'Debug: Log Store State',
                category: 'DEBUG',
                action: () => {
                    console.log('[L4 Debug] Store state:', useDashboardStore.getState())
                },
            },
            {
                id: 'debug_fire_alert_eval',
                label: 'Debug: Force Alert Evaluation',
                category: 'DEBUG',
                action: () => {
                    AlertEngine.evaluate(useDashboardStore.getState())
                },
            },
        ] as Command[] : []),
    ]

    return commands
}

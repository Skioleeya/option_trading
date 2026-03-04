/**
 * l4_ui — Smoke Tester (Phase 5)
 * ──────────────────────────────────────
 * Injects a global window.mockL4 object in development to allow
 * manual verification of the frontend UI and state changes without
 * requiring the L3 Python backend.
 */

import { useDashboardStore } from './store/dashboardStore'
import { L4Rum } from './observability/l4_rum'
import { useAlertStore } from './alerts/alertStore'

export function injectSmokeTester() {
    if (typeof window === 'undefined' || import.meta.env.PROD) return

        ; (window as any).mockL4 = {
            /**
             * 1. Force top-level spot update
             * Usage: mockL4.setSpot(560.5)
             */
            setSpot: (price: number) => {
                useDashboardStore.setState({ spot: price })
                console.log(`[Smoke Test] Overriding spot to ${price}`)
            },

            /**
             * 2. Push full payload manually
             */
            injectPayload: (payload: any) => {
                useDashboardStore.getState().applyFullUpdate(payload)
                console.log(`[Smoke Test] Injected full payload`)
            },

            /**
             * 3. Simulate Alert (bypassing AlertEngine logic for UI testing)
             */
            triggerAlert: (severity: 'info' | 'warning' | 'critical', category: string, title: string, body: string) => {
                useAlertStore.getState().push({
                    id: `smoke_${Date.now()}`,
                    timestamp: Date.now(),
                    severity,
                    category: category as any,
                    title,
                    body,
                })
                console.log(`[Smoke Test] Injected alert: ${title}`)
            },

            /**
             * 4. Connection Simulation
             */
            simulateDisconnect: () => {
                useDashboardStore.getState().setConnectionStatus('disconnected')
                console.log('[Smoke Test] Connection status set to disconnected')
            },
            simulateConnect: () => {
                useDashboardStore.getState().setConnectionStatus('connected')
                console.log('[Smoke Test] Connection status set to connected')
            },

            /**
             * 5. Read current RUM metrics
             */
            getRum: () => {
                const snap = L4Rum.snapshot()
                console.table(snap)
                return snap
            }
        }

    console.info(`[L4 Smoke Test] Injected window.mockL4. Use console to debug UI features without backend.
Commands:
  mockL4.setSpot(number)
  mockL4.triggerAlert('critical', 'SIGNAL', 'Test Alert', 'This is a test trigger')
  mockL4.simulateDisconnect()
  mockL4.simulateConnect()
  mockL4.injectPayload({...})
  mockL4.getRum()
`)
}

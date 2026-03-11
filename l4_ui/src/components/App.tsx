/**
 * l4_ui — App.tsx (Phase 4: Command Palette + Alert Engine)
 * ─────────────────────────────────────────────────────────────────
 * Phase 4 additions (zero layout impact):
 *   • CommandPalette rendered as portal-sibling (Ctrl+K)
 *   • AlertToast rendered as portal-sibling (bottom-right stack)
 *   • AlertEngine.start() called on mount, stop() on unmount
 *
 * Layout / DOM / CSS: 100% UNCHANGED
 */

import React, { useEffect } from 'react'
import '../index.css'
import { useDashboardWS } from '../hooks/useDashboardWS'
import { useDashboardStore } from '../store/dashboardStore'
import { Header } from './center/Header'
import { GexStatusBar } from './center/GexStatusBar'
import { AtmDecayOverlay } from './center/AtmDecayOverlay'
import { LeftPanel } from './left/LeftPanel'
import { RightPanel } from './right/RightPanel'
import { AtmDecayChart } from './center/AtmDecayChart'
import { L4Rum } from '../observability/l4_rum'
import { AlertEngine } from '../alerts/alertEngine'
import { AlertToast } from './AlertToast'
import { CommandPalette } from './CommandPalette'
import { DebugOverlay } from './DebugOverlay'
import { deriveMarketStatus } from './center/headerState'
import { decodeHistoryRows } from '../lib/historyColumnar'
import type { AtmDecay } from '../types/dashboard'
import { runtimeConfig } from '../config/runtime'

function toNullableNumber(raw: unknown): number | null {
    if (raw === null || raw === undefined) return null
    if (typeof raw === 'number') return Number.isFinite(raw) ? raw : null
    if (typeof raw === 'string' && raw.trim()) {
        const num = Number(raw)
        return Number.isFinite(num) ? num : null
    }
    return null
}

function toOptionalIsoString(raw: unknown): string | undefined {
    if (typeof raw !== 'string' || !raw.trim()) return undefined
    const d = new Date(raw)
    if (Number.isNaN(d.getTime())) return undefined
    return raw
}

function toOptionalBoolean(raw: unknown): boolean | undefined {
    if (typeof raw === 'boolean') return raw
    if (typeof raw !== 'string') return undefined
    const text = raw.trim().toLowerCase()
    if (text === 'true' || text === '1') return true
    if (text === 'false' || text === '0') return false
    return undefined
}

function normalizeAtmHistoryRows(rows: Record<string, unknown>[]): AtmDecay[] {
    return rows.map((row) => ({
        strike: toNullableNumber(row.strike),
        base_strike: toNullableNumber(row.base_strike),
        locked_at: typeof row.locked_at === 'string' ? row.locked_at : null,
        straddle_pct: toNullableNumber(row.straddle_pct),
        call_pct: toNullableNumber(row.call_pct),
        put_pct: toNullableNumber(row.put_pct),
        timestamp: toOptionalIsoString(row.timestamp),
        strike_changed: toOptionalBoolean(row.strike_changed),
    }))
}

// ─────────────────────────────────────────────────────────────────────────────
// App
// ─────────────────────────────────────────────────────────────────────────────

export const App: React.FC = () => {
    useDashboardWS()
    const [debugOpen, setDebugOpen] = React.useState(false)
    const moduleFlags = runtimeConfig.flags

    useEffect(() => {
        L4Rum.markFmp()
        AlertEngine.start()
        console.info(
            '[L4 Runtime] center_v2=%s right_v2=%s left_v2=%s chart_engine=%s ws=%s api=%s',
            moduleFlags.centerV2,
            moduleFlags.rightV2,
            moduleFlags.leftV2,
            runtimeConfig.chartEngine,
            runtimeConfig.wsUrl,
            runtimeConfig.apiBase,
        )

        const handleOverlayToggle = () => setDebugOpen(prev => !prev)
        window.addEventListener('l4:toggle_debug_overlay', handleOverlayToggle)

        // Cold boot: hydrate chart with minimal ATM history fields before websocket.
        const atmHistoryFields = 'timestamp,straddle_pct,call_pct,put_pct,strike_changed'
        const fetchAtmHistoryV2 = async (): Promise<AtmDecay[] | null> => {
            const url = `${runtimeConfig.apiBase}/api/atm-decay/history?fields=${encodeURIComponent(atmHistoryFields)}&schema=v2`
            try {
                const res = await fetch(url)
                const data = await res.json()
                const rows = decodeHistoryRows(data, 'history')
                return rows ? normalizeAtmHistoryRows(rows) : null
            } catch (err) {
                console.warn('[App] ATM history fetch failed (schema=v2):', err)
                return null
            }
        }

        ; (async () => {
            const rows = await fetchAtmHistoryV2()
            if (rows && rows.length > 0) {
                useDashboardStore.getState().hydrateAtmHistory(rows)
            }
        })()

        return () => {
            AlertEngine.stop()
            window.removeEventListener('l4:toggle_debug_overlay', handleOverlayToggle)
        }
    }, [moduleFlags.centerV2, moduleFlags.leftV2, moduleFlags.rightV2])

    const marketStatus = deriveMarketStatus()

    return (
        <>
            <DebugOverlay open={debugOpen} onClose={() => setDebugOpen(false)} />
            {/* ─── Portal siblings (no layout impact) ─────────────────────────── */}
            <CommandPalette />
            <AlertToast />

            {/* ─── Main layout ───────────────────────────────────────────────── */}
            <div
                className="flex flex-col h-screen w-screen overflow-hidden bg-bg-primary"
                data-center-module={moduleFlags.centerV2 ? 'v2' : 'stable'}
                data-right-module={moduleFlags.rightV2 ? 'v2' : 'stable'}
                data-left-module={moduleFlags.leftV2 ? 'v2' : 'stable'}
            >
                <Header marketStatus={marketStatus} />

                <div className="flex flex-1 overflow-hidden">
                    {/* LEFT PANEL */}
                    <LeftPanel mode={moduleFlags.leftV2 ? 'v2' : 'stable'} />

                    {/* CENTER PANEL */}
                    <div className="relative flex flex-col flex-1 overflow-hidden bg-[#090a0c]">
                        <div className="flex-1 overflow-hidden relative"><AtmDecayChart /></div>
                        <div className="absolute top-3 left-3 z-10 pointer-events-none">
                            <div className="pointer-events-auto"><AtmDecayOverlay /></div>
                        </div>
                        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
                            <div className="pointer-events-auto"><GexStatusBar /></div>
                        </div>
                    </div>

                    {/* RIGHT PANEL */}
                    <div className="flex flex-col border-l border-bg-border overflow-y-auto"
                        style={{ width: '320px', minWidth: '320px' }}>
                        <RightPanel mode={moduleFlags.rightV2 ? 'v2' : 'stable'} />
                    </div>
                </div>
            </div>
        </>
    )
}

/**
 * l4_ui — App.tsx (Phase 4: Command Palette + Alert Engine)
 * ─────────────────────────────────────────────────────────────────
 * Phase 4 additions (zero layout impact):
 *   • CommandPalette rendered as portal-sibling (Ctrl+K)
 *   • AlertToast rendered as portal-sibling (bottom-right stack)
 *   • AlertEngine.start() called on mount, stop() on unmount
 *
 * Layout now uses viewport-driven layout tokens; whole-app transform scaling was removed.
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
import { buildLayoutScaleVars } from '../lib/layoutScale'
import { useLayoutScale } from '../hooks/useLayoutScale'

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
    const [profilingForced, setProfilingForced] = React.useState(false)
    const [atmHistoryLoadError, setAtmHistoryLoadError] = React.useState<string | null>(null)
    const moduleFlags = runtimeConfig.flags
    const { scale, profile } = useLayoutScale()
    const profilingEnabled = debugOpen || profilingForced

    useEffect(() => {
        L4Rum.setProfilingEnabled(profilingEnabled)
        return () => L4Rum.setProfilingEnabled(false)
    }, [profilingEnabled])

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
        const handleProfilingToggle = (event: Event) => {
            const detail = (event as CustomEvent<boolean>).detail
            setProfilingForced(detail === true)
        }
        window.addEventListener('l4:toggle_debug_overlay', handleOverlayToggle)
        window.addEventListener('l4:set_profiling_enabled', handleProfilingToggle as EventListener)

        // Cold boot: hydrate chart with minimal ATM history fields before websocket.
        const atmHistoryFields = 'timestamp,straddle_pct,call_pct,put_pct,strike_changed'
        const fetchAtmHistoryV2 = async (): Promise<AtmDecay[]> => {
            const url = `${runtimeConfig.apiBase}/api/atm-decay/history?fields=${encodeURIComponent(atmHistoryFields)}&schema=v2`
            const res = await fetch(url)
            if (!res.ok) {
                const body = await res.text()
                throw new Error(
                    `[App] ATM history request failed status=${res.status} body=${body.slice(0, 256)}`
                )
            }
            const data = await res.json()
            const rows = decodeHistoryRows(data, 'history')
            if (!rows) {
                throw new Error('[App] ATM history response is invalid for schema=v2')
            }
            return normalizeAtmHistoryRows(rows)
        }

        ; (async () => {
            try {
                const rows = await fetchAtmHistoryV2()
                if (rows.length === 0) {
                    throw new Error('[App] ATM history is empty; persistence is required in strict mode.')
                }
                const last = rows[rows.length - 1]
                console.info(
                    '[L4 ATM] history hydrate rows=%s last_ts=%s straddle=%s call=%s put=%s',
                    rows.length,
                    last?.timestamp ?? 'NA',
                    last?.straddle_pct ?? 'NA',
                    last?.call_pct ?? 'NA',
                    last?.put_pct ?? 'NA',
                )
                useDashboardStore.getState().hydrateAtmHistory(rows)
                setAtmHistoryLoadError(null)
            } catch (err) {
                const message = err instanceof Error ? err.message : String(err)
                setAtmHistoryLoadError(message)
                console.error('[L4 ATM] strict history hydrate failed:', message)
            }
        })()

        return () => {
            AlertEngine.stop()
            window.removeEventListener('l4:toggle_debug_overlay', handleOverlayToggle)
            window.removeEventListener('l4:set_profiling_enabled', handleProfilingToggle as EventListener)
        }
    }, [moduleFlags.centerV2, moduleFlags.leftV2, moduleFlags.rightV2])

    const marketStatus = deriveMarketStatus()
    const layoutScaleStyle = buildLayoutScaleVars(scale, profile) as React.CSSProperties

    return (
        <div
            className="h-screen w-screen overflow-hidden bg-bg-primary"
            style={layoutScaleStyle}
            data-layout-profile={profile}
        >
            {debugOpen ? <DebugOverlay open onClose={() => setDebugOpen(false)} /> : null}
            {/* ─── Portal siblings (no layout impact) ─────────────────── */}
            <CommandPalette />
            <AlertToast />

            {/* ─── Main layout ───────────────────────────────────────── */}
            <div
                className="flex flex-col h-full w-full overflow-hidden bg-bg-primary"
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
                        {atmHistoryLoadError && (
                            <div
                                className="absolute z-30 text-red-400 border border-red-500/40 bg-black/75"
                                style={{
                                    top: 'var(--l4-space-3)',
                                    right: 'var(--l4-space-3)',
                                    padding: '6px 10px',
                                    fontSize: 'var(--l4-font-8)',
                                }}
                            >
                                ATM HISTORY FAST-FAIL: {atmHistoryLoadError}
                            </div>
                        )}
                        <div className="flex-1 overflow-hidden relative"><AtmDecayChart /></div>
                        <div
                            className="absolute z-10 pointer-events-none"
                            style={{ top: 'var(--l4-space-3)', left: 'var(--l4-space-3)' }}
                        >
                            <div className="pointer-events-auto"><AtmDecayOverlay /></div>
                        </div>
                        <div
                            className="absolute left-1/2 -translate-x-1/2 z-20 pointer-events-none"
                            style={{ bottom: 'var(--l4-space-8)' }}
                        >
                            <div className="pointer-events-auto"><GexStatusBar /></div>
                        </div>
                    </div>

                    {/* RIGHT PANEL */}
                    <div
                        className="flex flex-col border-l border-bg-border overflow-y-auto"
                        style={{ width: 'var(--l4-right-w)', minWidth: 'var(--l4-right-w)' }}
                    >
                        <RightPanel mode={moduleFlags.rightV2 ? 'v2' : 'stable'} />
                    </div>
                </div>
            </div>
        </div>
    )
}

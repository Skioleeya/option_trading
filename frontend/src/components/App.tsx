import React from 'react'
import '../index.css'
import { useDashboardWS } from '../hooks/useDashboardWS'
import { Header } from './center/Header'
import { GexStatusBar } from './center/GexStatusBar'
import { AtmDecayOverlay } from './center/AtmDecayOverlay'
import { WallMigration } from './left/WallMigration'
import { DepthProfile } from './left/DepthProfile'
import { MicroStats } from './left/MicroStats'
import { DecisionEngine } from './right/DecisionEngine'
import { ActiveOptions } from './right/ActiveOptions'
import type { AtmDecay } from '../types/dashboard'

// ============================================================================
// TradingView Widget placeholder
// ============================================================================
const TradingViewChart: React.FC<{ spot: number | null }> = ({ spot: _spot }) => (
    <div className="relative w-full h-full bg-bg-primary flex items-center justify-center">
        {/* TradingView widget will be embedded here */}
        <div id="tradingview-widget" className="w-full h-full" />
        {/* Fallback if TradingView not loaded */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span className="mono text-xs text-text-muted">
                TradingView Widget — SPX / ATM Decay Chart
            </span>
        </div>
    </div>
)

// ============================================================================
// Main App
// ============================================================================
export const App: React.FC = () => {
    const { status, payload } = useDashboardWS()

    const spot = payload?.spot ?? null
    const agentG = payload?.agent_g ?? null
    const agentBData = agentG?.data?.agent_b?.data
    const fused = agentG?.data?.fused_signal ?? null

    // Derived values
    const netGex = agentBData?.net_gex ?? null
    const callWall = agentBData?.gamma_walls?.call_wall ?? null
    const putWall = agentBData?.gamma_walls?.put_wall ?? null
    const flipLevel = agentBData?.gamma_flip_level ?? null
    const perStrikeGex = agentBData?.per_strike_gex ?? []
    const ivPct = agentBData?.spy_atm_iv ?? null
    const ivRegime = fused?.iv_regime ?? 'NORMAL'

    // Microstructure
    const mtfConsensus = agentBData?.mtf_consensus

    // ── DECOUPLED UI Architecture ──
    // Backend computes the badges and states precisely, React blindly renders them.
    const uiState = agentG?.data?.ui_state ?? {
        net_gex: { label: '—', badge: 'badge-neutral' },
        wall_dyn: { label: '—', badge: 'badge-neutral' },
        vanna: { label: '—', badge: 'badge-neutral' },
        momentum: { label: '—', badge: 'badge-neutral' }
    }

    // ATM Decay (computed separately — requires opening ATM)
    const atm: AtmDecay = {
        atm_strike: null, // Will be populated from backend
        straddle_pct: null,
        call_pct: null,
        put_pct: null,
    }

    // Market status
    const now = new Date()
    const hour = now.getHours()
    const marketStatus = hour >= 9 && hour < 16 ? 'OPEN' : 'CLOSE'

    return (
        <div className="flex flex-col h-screen w-screen overflow-hidden bg-bg-primary">
            {/* ═══════════════ HEADER ═══════════════ */}
            <Header
                spot={spot}
                ivPct={ivPct}
                ivRegime={ivRegime}
                status={status}
                marketStatus={marketStatus}
                as_of={payload?.timestamp ?? null}
            />

            {/* ═══════════════ 3-COLUMN BODY ═══════════════ */}
            <div className="flex flex-1 overflow-hidden">

                {/* ── LEFT PANEL (ANALYSIS / DEFENSE) ── */}
                <div className="flex flex-col border-r panel-border-right overflow-hidden"
                    style={{ width: '220px', minWidth: '220px' }}>

                    {/* GAMMA STRUCTURE header */}
                    <div className="flex items-center justify-between px-2 py-1 border-b border-bg-border">
                        <span className="section-header">GAMMA STRUCTURE</span>
                        <span className="section-header text-text-muted">RADAR &amp; DEPTH</span>
                    </div>

                    {/* Wall Migration */}
                    <WallMigration
                        callWall={callWall}
                        putWall={putWall}
                    />

                    {/* Depth Profile - takes remaining space */}
                    <div className="flex-1 overflow-hidden border-t border-bg-border">
                        <div className="flex items-center gap-2 px-2 py-0.5 border-b border-bg-border">
                            <span className="section-header">DEPTH PROFILE</span>
                        </div>
                        <DepthProfile
                            perStrikeGex={perStrikeGex}
                            spot={spot}
                            flipLevel={flipLevel}
                        />
                    </div>

                    {/* Micro Stats */}
                    <div className="flex-1 min-h-0 min-w-0">
                        <MicroStats
                            uiState={uiState}
                            sideState={mtfConsensus?.consensus ?? ''}
                        />
                    </div>
                </div>

                {/* ── CENTER PANEL (CHART) ── */}
                <div className="flex flex-col flex-1 overflow-hidden">
                    {/* Chart area */}
                    <div className="relative flex-1 overflow-hidden">
                        <TradingViewChart spot={spot} />

                        {/* ATM Decay glassmorphism overlay */}
                        <div className="absolute top-2 left-2 z-10">
                            <AtmDecayOverlay atm={atm} spot={spot} />
                        </div>
                    </div>

                    {/* GEX Status Bar */}
                    <GexStatusBar
                        netGex={netGex}
                        callWall={callWall}
                        flipLevel={flipLevel}
                        putWall={putWall}
                    />
                </div>

                {/* ── RIGHT PANEL (TACTICAL OFFENSE) ── */}
                <div className="flex flex-col border-l panel-border-right overflow-y-auto"
                    style={{ width: '260px', minWidth: '260px' }}>

                    {/* Header */}
                    <div className="flex items-center justify-between px-2 py-1 border-b border-bg-border">
                        <div className="flex items-center gap-1.5">
                            <div className="w-1.5 h-1.5 rounded-full bg-accent-green dot-live" />
                            <span className="section-header">TACTICAL OFFENSE</span>
                        </div>
                    </div>

                    {/* Decision Engine */}
                    <DecisionEngine fused={fused} />

                    {/* Tactical Triad */}
                    <div className="border-t border-bg-border p-2">
                        <div className="flex items-center justify-between mb-2">
                            <span className="section-header">TACTICAL TRIAD</span>
                            <span className="section-header text-text-muted">S-VOL / CHARM / VRP</span>
                        </div>
                        <div className="grid grid-cols-3 gap-1">
                            {[
                                { label: 'VRP', sub: 'BREAKOUT' },
                                { label: 'CHARM', sub: 'REVERSAL' },
                                { label: 'S-VOL', sub: 'FLIP RISK' },
                            ].map((item) => (
                                <div key={item.label}
                                    className="border border-bg-border rounded p-1.5 space-y-1">
                                    <div className="mono text-xs text-text-secondary font-bold">{item.label}</div>
                                    <div className="mono text-sm font-bold text-text-primary">—</div>
                                    <div className="section-header text-text-muted">{item.sub}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Skew Dynamics */}
                    <div className="border-t border-bg-border p-2">
                        <div className="flex items-center justify-between mb-1">
                            <span className="section-header">SKEW DYNAMICS</span>
                            <span className="section-header text-text-muted">IV SKEW ANALYSIS</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5">
                                <div className="w-3 h-3 rounded-full bg-bg-border flex items-center justify-center">
                                    <div className="w-1.5 h-1.5 rounded-full bg-text-secondary" />
                                </div>
                                <div>
                                    <div className="section-header">IV SKEW</div>
                                    <div className="badge badge-neutral text-2xs">NEUTRAL</div>
                                </div>
                            </div>
                            <span className="mono text-xl font-bold text-text-primary">—</span>
                        </div>
                    </div>

                    {/* Active Options */}
                    <div className="border-t border-bg-border flex-1">
                        <ActiveOptions options={[]} />
                    </div>

                    {/* MTF Flow */}
                    <div className="border-t border-bg-border p-2">
                        <div className="section-header mb-1.5">MTF FLOW</div>
                        <div className="grid grid-cols-3 gap-1">
                            {['1M', '5M', '15M'].map((tf) => (
                                <div key={tf}
                                    className="flex items-center justify-between px-2 py-1 border border-bg-border rounded">
                                    <span className="mono text-2xs text-text-secondary">{tf}</span>
                                    <div className="w-1.5 h-1.5 rounded-full bg-text-muted" />
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

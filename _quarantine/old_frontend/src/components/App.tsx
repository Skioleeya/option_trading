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
import { TacticalTriad } from './right/TacticalTriad'
import { SkewDynamics } from './right/SkewDynamics'
import { ActiveOptions } from './right/ActiveOptions'
import { MtfFlow } from './right/MtfFlow'
import type { AtmDecay } from '../types/dashboard'


import { useEffect, useState, useMemo } from 'react'

const API_BASE = 'http://localhost:8001'

import { AtmDecayChart } from './center/AtmDecayChart'

// ============================================================================
// Main App
// ============================================================================
export const App: React.FC = () => {
    const { status, payload } = useDashboardWS()
    const [atmHistory, setAtmHistory] = useState<AtmDecay[]>([])

    // 1. Fetch history on connection
    useEffect(() => {
        if (status === 'connected') {
            fetch(`${API_BASE}/api/atm-decay/history`)
                .then(res => res.json())
                .then(data => {
                    if (data && data.history) {
                        setAtmHistory(data.history)
                    }
                })
                .catch(err => console.error("Failed to fetch ATM history:", err))
        }
    }, [status])

    // 2. Extract and merge latest tick
    const atm = useMemo(() => {
        const latest = payload?.agent_g?.data?.ui_state?.atm
        if (latest) {
            // Append to history if it's a new timestamp
            setAtmHistory(prev => {
                const alreadyExists = prev.some(t => t.timestamp === latest.timestamp)
                if (alreadyExists) return prev
                return [...prev, latest]
            })
        }
        return latest ?? null
    }, [payload])

    const spot = payload?.spot ?? null
    const agentG = payload?.agent_g ?? null
    const fused = agentG?.data?.fused_signal ?? null

    // Derived values
    const netGex = agentG?.data?.net_gex ?? null
    const callWall = agentG?.data?.gamma_walls?.call_wall ?? null
    const putWall = agentG?.data?.gamma_walls?.put_wall ?? null
    const flipLevel = agentG?.data?.gamma_flip_level ?? null
    const ivPct = agentG?.data?.spy_atm_iv ?? null
    const ivRegime = fused?.iv_regime ?? 'NORMAL'

    // ── DECOUPLED UI Architecture ──
    // Backend computes the badges and states precisely, React blindly renders them.
    if (payload && !payload.agent_g?.data?.ui_state) {
        console.warn("[L4 App] Backend violated invariant: ui_state missing from payload. Using hardcoded fallback.");
    }

    const uiState: any = agentG?.data?.ui_state ?? {
        micro_stats: {
            net_gex: { label: '—', badge: 'badge-neutral' },
            wall_dyn: { label: '—', badge: 'badge-neutral' },
            vanna: { label: '—', badge: 'badge-neutral' },
            momentum: { label: '—', badge: 'badge-neutral' }
        },
        tactical_triad: null,
        skew_dynamics: null,
        active_options: [],
        mtf_flow: null,
        wall_migration: [],
        depth_profile: [],
        macro_volume_map: {}
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
                    style={{ width: '280px', minWidth: '280px' }}>

                    {/* Wall Migration */}
                    <WallMigration rows={uiState.wall_migration} />

                    {/* Depth Profile - takes remaining space */}
                    <div className="flex-1 overflow-hidden border-t border-bg-border flex flex-col">
                        <div className="shrink-0 flex items-center justify-between px-2 py-1.5 border-b border-bg-border bg-[#0a0a0a]">
                            <span className="section-header text-[#e0e0e0] font-bold tracking-widest text-[11px] uppercase">DEPTH PROFILE</span>
                            <div className="flex items-center gap-3 text-3xs font-medium tracking-wide pr-1 text-white/80">
                                <span className="flex items-center gap-1.5"><div className="w-[5px] h-[5px] rounded-full bg-market-down"></div>Put</span>
                                <span className="flex items-center gap-1.5"><div className="w-[5px] h-[5px] rounded-full bg-market-up"></div>Call</span>
                            </div>
                        </div>
                        <DepthProfile rows={uiState.depth_profile} macroVolumeMap={uiState.macro_volume_map} spot={spot} />
                    </div>

                    {/* Micro Stats */}
                    <div className="shrink-0 flex-none border-t border-bg-border">
                        <MicroStats
                            uiState={uiState.micro_stats}
                        />
                    </div>
                </div>

                {/* ── CENTER PANEL (CHART) ── */}
                <div className="relative flex flex-col flex-1 overflow-hidden bg-[#090a0c]">
                    <div className="flex-1 overflow-hidden relative">
                        <AtmDecayChart data={atmHistory} />
                    </div>

                    {/* ATM Decay glassmorphism overlay */}
                    <div className="absolute top-3 left-3 z-10 pointer-events-none">
                        <div className="pointer-events-auto">
                            <AtmDecayOverlay atm={atm} spot={spot} history={atmHistory} />
                        </div>
                    </div>

                    {/* GEX Status Bar — floats above TradingView time axis */}
                    <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
                        <div className="pointer-events-auto">
                            <GexStatusBar
                                netGex={netGex}
                                callWall={callWall}
                                flipLevel={flipLevel}
                                putWall={putWall}
                            />
                        </div>
                    </div>
                </div>

                {/* ── RIGHT PANEL (TACTICAL OFFENSE) ── */}
                <div className="flex flex-col border-l border-bg-border overflow-y-auto"
                    style={{ width: '320px', minWidth: '320px' }}>

                    {/* Decision Engine */}
                    <DecisionEngine fused={fused} />

                    {/* Tactical Triad */}
                    <TacticalTriad uiState={uiState.tactical_triad} />

                    {/* Skew Dynamics */}
                    <SkewDynamics uiState={uiState.skew_dynamics} />

                    {/* Active Options */}
                    <div className="border-t border-bg-border flex-1">
                        <ActiveOptions options={uiState.active_options ?? []} />
                    </div>

                    {/* MTF Flow */}
                    <MtfFlow uiState={uiState.mtf_flow} />
                </div>
            </div>
        </div>
    )
}

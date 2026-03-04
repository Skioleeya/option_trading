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
import { AtmDecayChart } from './center/AtmDecayChart'
import { L4Rum } from '../observability/l4_rum'
import { AlertEngine } from '../alerts/alertEngine'
import { AlertToast } from './AlertToast'
import { CommandPalette } from './CommandPalette'

// ─────────────────────────────────────────────────────────────────────────────
// App
// ─────────────────────────────────────────────────────────────────────────────

export const App: React.FC = () => {
    useDashboardWS()

    useEffect(() => {
        L4Rum.markFmp()
        AlertEngine.start()
        return () => AlertEngine.stop()
    }, [])

    const now = new Date()
    const marketStatus = now.getHours() >= 9 && now.getHours() < 16 ? 'OPEN' : 'CLOSE'

    return (
        <>
            {/* ─── Portal siblings (no layout impact) ─────────────────────────── */}
            <CommandPalette />
            <AlertToast />

            {/* ─── Main layout ───────────────────────────────────────────────── */}
            <div className="flex flex-col h-screen w-screen overflow-hidden bg-bg-primary">
                <Header marketStatus={marketStatus} />

                <div className="flex flex-1 overflow-hidden">
                    {/* LEFT PANEL */}
                    <div className="flex flex-col border-r panel-border-right overflow-hidden"
                        style={{ width: '280px', minWidth: '280px' }}>
                        <WallMigration />
                        <div className="flex-1 overflow-hidden border-t border-bg-border flex flex-col">
                            <div className="shrink-0 flex items-center justify-between px-2 py-1.5 border-b border-bg-border bg-[#0a0a0a]">
                                <span className="section-header text-[#e0e0e0] font-bold tracking-widest text-[11px] uppercase">DEPTH PROFILE</span>
                                <div className="flex items-center gap-3 text-3xs font-medium tracking-wide pr-1 text-white/80">
                                    <span className="flex items-center gap-1.5"><div className="w-[5px] h-[5px] rounded-full bg-market-down"></div>Put</span>
                                    <span className="flex items-center gap-1.5"><div className="w-[5px] h-[5px] rounded-full bg-market-up"></div>Call</span>
                                </div>
                            </div>
                            <DepthProfile />
                        </div>
                        <div className="shrink-0 flex-none border-t border-bg-border"><MicroStats /></div>
                    </div>

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
                        <DecisionEngine />
                        <TacticalTriad />
                        <SkewDynamics />
                        <div className="border-t border-bg-border flex-1"><ActiveOptions /></div>
                        <MtfFlow />
                    </div>
                </div>
            </div>
        </>
    )
}

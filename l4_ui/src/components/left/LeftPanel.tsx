import React, { memo } from 'react'
import { useDashboardStore, selectPayload } from '../../store/dashboardStore'
import { DepthProfile } from './DepthProfile'
import { MicroStats } from './MicroStats'
import { WallMigration } from './WallMigration'
import { deriveLeftPanelContracts } from './leftPanelModel'

export interface LeftPanelProps {
    mode: 'v2' | 'stable'
}

function LeftPanelFrame({ children }: { children: React.ReactNode }): React.JSX.Element {
    return (
        <div
            className="l4-left-panel flex flex-col border-r panel-border-right overflow-hidden"
            style={{ width: 'var(--l4-left-w)', minWidth: 'var(--l4-left-w)' }}
        >
            {children}
        </div>
    )
}

const LeftPanelLive: React.FC = memo(() => (
    <LeftPanelFrame>
        <WallMigration />
        <div className="flex-1 overflow-hidden border-t border-bg-border flex flex-col">
            <div className="shrink-0 flex items-center justify-between border-b border-bg-border bg-[#0a0a0a]" style={{ padding: 'var(--l4-panel-pad)' }}>
                <span className="section-header text-[#e0e0e0] font-bold tracking-widest uppercase" style={{ fontSize: 'var(--l4-font-11)' }}>DEPTH PROFILE</span>
                <div className="flex items-center font-medium tracking-wide text-white/80" style={{ gap: 'var(--l4-panel-gap)', fontSize: 'var(--l4-font-9)' }}>
                    <span className="flex items-center gap-1.5"><div className="rounded-full bg-market-down" style={{ width: 'var(--l4-dot-xs)', height: 'var(--l4-dot-xs)' }}></div>Put</span>
                    <span className="flex items-center gap-1.5"><div className="rounded-full bg-market-up" style={{ width: 'var(--l4-dot-xs)', height: 'var(--l4-dot-xs)' }}></div>Call</span>
                </div>
            </div>
            <DepthProfile />
        </div>
        <div className="shrink-0 flex-none border-t border-bg-border">
            <MicroStats />
        </div>
    </LeftPanelFrame>
))

LeftPanelLive.displayName = 'LeftPanelLive'

const LeftPanelStable: React.FC = memo(() => {
    const payload = useDashboardStore(selectPayload)
    const stableContracts = deriveLeftPanelContracts(payload)

    return (
        <LeftPanelFrame>
            <WallMigration rows={stableContracts.wallMigrationRows} preferProp />
            <div className="flex-1 overflow-hidden border-t border-bg-border flex flex-col">
                <div className="shrink-0 flex items-center justify-between border-b border-bg-border bg-[#0a0a0a]" style={{ padding: 'var(--l4-panel-pad)' }}>
                    <span className="section-header text-[#e0e0e0] font-bold tracking-widest uppercase" style={{ fontSize: 'var(--l4-font-11)' }}>DEPTH PROFILE</span>
                    <div className="flex items-center font-medium tracking-wide text-white/80" style={{ gap: 'var(--l4-panel-gap)', fontSize: 'var(--l4-font-9)' }}>
                        <span className="flex items-center gap-1.5"><div className="rounded-full bg-market-down" style={{ width: 'var(--l4-dot-xs)', height: 'var(--l4-dot-xs)' }}></div>Put</span>
                        <span className="flex items-center gap-1.5"><div className="rounded-full bg-market-up" style={{ width: 'var(--l4-dot-xs)', height: 'var(--l4-dot-xs)' }}></div>Call</span>
                    </div>
                </div>
                <DepthProfile
                    rows={stableContracts.depthProfileRows}
                    macroVolumeMap={stableContracts.macroVolumeMap}
                    spot={stableContracts.spot}
                    gammaWalls={stableContracts.gammaWalls}
                    flipLevel={stableContracts.flipLevel}
                    preferProp
                />
            </div>
            <div className="shrink-0 flex-none border-t border-bg-border">
                <MicroStats uiState={stableContracts.microStats ?? undefined} preferProp />
            </div>
        </LeftPanelFrame>
    )
})

LeftPanelStable.displayName = 'LeftPanelStable'

export const LeftPanel: React.FC<LeftPanelProps> = memo(({ mode }) => {
    return mode === 'stable' ? <LeftPanelStable /> : <LeftPanelLive />
})

LeftPanel.displayName = 'LeftPanel'

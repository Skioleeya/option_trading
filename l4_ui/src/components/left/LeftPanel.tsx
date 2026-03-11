import React, { memo } from 'react'
import { useDashboardStore, selectPayload } from '../../store/dashboardStore'
import { DepthProfile } from './DepthProfile'
import { MicroStats } from './MicroStats'
import { WallMigration } from './WallMigration'
import { deriveLeftPanelContracts, type LeftPanelContracts } from './leftPanelModel'

export interface LeftPanelProps {
    mode: 'v2' | 'stable'
}

export const LeftPanel: React.FC<LeftPanelProps> = memo(({ mode }) => {
    const payload = useDashboardStore(selectPayload)
    const stableContracts: LeftPanelContracts = deriveLeftPanelContracts(payload)

    const isStable = mode === 'stable'

    return (
        <div className="flex flex-col border-r panel-border-right overflow-hidden"
            style={{ width: '280px', minWidth: '280px' }}>
            <WallMigration
                rows={isStable ? stableContracts.wallMigrationRows : undefined}
                preferProp={isStable}
            />
            <div className="flex-1 overflow-hidden border-t border-bg-border flex flex-col">
                <div className="shrink-0 flex items-center justify-between px-2 py-1.5 border-b border-bg-border bg-[#0a0a0a]">
                    <span className="section-header text-[#e0e0e0] font-bold tracking-widest text-[11px] uppercase">DEPTH PROFILE</span>
                    <div className="flex items-center gap-3 text-3xs font-medium tracking-wide pr-1 text-white/80">
                        <span className="flex items-center gap-1.5"><div className="w-[5px] h-[5px] rounded-full bg-market-down"></div>Put</span>
                        <span className="flex items-center gap-1.5"><div className="w-[5px] h-[5px] rounded-full bg-market-up"></div>Call</span>
                    </div>
                </div>
                <DepthProfile
                    rows={isStable ? stableContracts.depthProfileRows : undefined}
                    macroVolumeMap={isStable ? stableContracts.macroVolumeMap : undefined}
                    spot={isStable ? stableContracts.spot : undefined}
                    gammaWalls={isStable ? stableContracts.gammaWalls : undefined}
                    flipLevel={isStable ? stableContracts.flipLevel : undefined}
                    preferProp={isStable}
                />
            </div>
            <div className="shrink-0 flex-none border-t border-bg-border">
                <MicroStats
                    uiState={isStable ? stableContracts.microStats ?? undefined : undefined}
                    preferProp={isStable}
                />
            </div>
        </div>
    )
})

LeftPanel.displayName = 'LeftPanel'

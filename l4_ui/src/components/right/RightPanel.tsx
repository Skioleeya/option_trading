import React, { memo } from 'react'
import { useDashboardStore, selectPayload } from '../../store/dashboardStore'
import { ActiveOptions } from './ActiveOptions'
import { DecisionEngine } from './DecisionEngine'
import { MtfFlow } from './MtfFlow'
import { SkewDynamics } from './SkewDynamics'
import { TacticalTriad } from './TacticalTriad'
import { deriveRightPanelContracts, type RightPanelContracts } from './rightPanelModel'

export interface RightPanelProps {
    mode: 'v2' | 'stable'
}

export const RightPanel: React.FC<RightPanelProps> = memo(({ mode }) => {
    const payload = useDashboardStore(selectPayload)
    const stableContracts: RightPanelContracts = deriveRightPanelContracts(payload)

    if (mode === 'stable') {
        return (
            <>
                <DecisionEngine fused={stableContracts.fused} netGex={stableContracts.netGex} preferProp />
                <TacticalTriad uiState={stableContracts.tacticalTriad} preferProp />
                <SkewDynamics uiState={stableContracts.skewDynamics} preferProp />
                <div className="border-t border-bg-border flex-1"><ActiveOptions options={stableContracts.activeOptions ?? []} preferProp /></div>
                <MtfFlow uiState={stableContracts.mtfFlow} preferProp />
            </>
        )
    }

    return (
        <>
            <DecisionEngine />
            <TacticalTriad />
            <SkewDynamics />
            <div className="border-t border-bg-border flex-1"><ActiveOptions /></div>
            <MtfFlow />
        </>
    )
})

RightPanel.displayName = 'RightPanel'

import React, { memo } from 'react'
import { useDashboardStore, selectPayload } from '../../store/dashboardStore'
import { ActiveOptions } from './ActiveOptions'
import { DecisionEngine } from './DecisionEngine'
import { MtfFlow } from './MtfFlow'
import { MmFlowCard } from './MmFlowCard'
import { SkewDynamics } from './SkewDynamics'
import { TacticalTriad } from './TacticalTriad'
import { deriveRightPanelContracts } from './rightPanelModel'

export interface RightPanelProps {
    mode: 'v2' | 'stable'
}

const RightPanelLive: React.FC = memo(() => (
    <>
        <DecisionEngine />
        <MmFlowCard />
        <TacticalTriad />
        <SkewDynamics />
        <div className="border-t border-bg-border"><ActiveOptions /></div>
        <MtfFlow />
    </>
))

RightPanelLive.displayName = 'RightPanelLive'

const RightPanelStable: React.FC = memo(() => {
    const payload = useDashboardStore(selectPayload)
    const stableContracts = deriveRightPanelContracts(payload)

    return (
        <>
            <DecisionEngine fused={stableContracts.fused} netGex={stableContracts.netGex} preferProp />
            <MmFlowCard metrics={stableContracts.mmFlow} preferProp />
            <TacticalTriad uiState={stableContracts.tacticalTriad} preferProp />
            <SkewDynamics uiState={stableContracts.skewDynamics} preferProp />
            <div className="border-t border-bg-border"><ActiveOptions options={stableContracts.activeOptions} preferProp /></div>
            <MtfFlow uiState={stableContracts.mtfFlow} preferProp />
        </>
    )
})

RightPanelStable.displayName = 'RightPanelStable'

export const RightPanel: React.FC<RightPanelProps> = memo(({ mode }) => {
    return mode === 'stable' ? <RightPanelStable /> : <RightPanelLive />
})

RightPanel.displayName = 'RightPanel'

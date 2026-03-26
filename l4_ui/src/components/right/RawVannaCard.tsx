import React, { memo } from 'react'
import { Activity } from 'lucide-react'
import { RAW_VANNA_ZERO, type RawVannaCardState } from './rightPanelModel'

interface Props {
    state?: RawVannaCardState | null
}

export const RawVannaCard: React.FC<Props> = memo(({ state }) => {
    const card = state ?? RAW_VANNA_ZERO

    return (
        <div className="border-t border-bg-border p-2">
            <div className="flex items-center justify-between mb-1">
                <span className="section-header">RAW VANNA</span>
                <span className="section-header text-text-muted">CANONICAL LIVE SUM</span>
            </div>
            <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                    <div className={`w-5 h-5 rounded flex items-center justify-center border ${card.borderClass} ${card.bgClass}`}>
                        <Activity size={10} className="text-text-secondary" />
                    </div>
                    <div>
                        <div className="section-header">NET_VANNA_RAW_SUM</div>
                        <div className={`badge ${card.badgeClass} text-[9px] px-1 py-0! tracking-wider`}>
                            {card.stateLabel}
                        </div>
                    </div>
                </div>
                <div className="text-right">
                    <div className={`mono text-lg font-bold ${card.colorClass}`}>{card.value}</div>
                    <div className="mono text-[9px] text-text-secondary/80">raw {card.exactValue}</div>
                </div>
            </div>
        </div>
    )
})

RawVannaCard.displayName = 'RawVannaCard'

import React from 'react'
import { fmtPrice } from '../../lib/utils'

interface Props {
    callWall: number | null
    putWall: number | null
    callHistory?: (number | null)[]
    putHistory?: (number | null)[]
}

export const WallMigration: React.FC<Props> = ({
    callWall, putWall,
    callHistory = [null, null],
    putHistory = [null, null],
}) => {
    const renderRow = (
        type: 'C' | 'P',
        history: (number | null)[],
        current: number | null,
        isCall: boolean
    ) => {
        const [h1, h2] = history
        const dotBg = isCall ? 'bg-accent-red' : 'bg-accent-green'

        return (
            <div className="flex items-center gap-0.5 h-7 px-1 py-0.5">
                {/* Type label */}
                <div className={`w-5 h-5 flex items-center justify-center rounded-sm text-2xs font-bold flex-shrink-0
          ${isCall ? 'text-market-up bg-wall-call' : 'text-market-down bg-wall-put'}`}>
                    {type}
                </div>

                {/* History cell 1 */}
                <div className="flex-1 flex items-center justify-center border border-bg-border bg-white/5 rounded-sm h-5">
                    <span className="mono text-2xs text-text-secondary">{h1 != null ? fmtPrice(h1) : '—'}</span>
                </div>

                {/* History cell 2 */}
                <div className="flex-1 flex items-center justify-center border border-bg-border bg-white/5 rounded-sm h-5">
                    <span className="mono text-2xs text-text-secondary">{h2 != null ? fmtPrice(h2) : '—'}</span>
                </div>

                {/* Current — AMBER GOLD highlighted box (matches screenshot) */}
                <div className="flex-1 flex items-center justify-center rounded-sm h-5"
                    style={{
                        border: '1px solid rgba(245, 158, 11, 0.7)',
                        boxShadow: '0 0 6px rgba(245, 158, 11, 0.25)',
                        background: 'rgba(245, 158, 11, 0.08)',
                    }}>
                    <span className="mono text-2xs font-bold text-accent-amber">
                        {current != null ? fmtPrice(current) : '—'}
                    </span>
                </div>

                {/* Status dot */}
                <div className={`w-2.5 h-2.5 rounded-full ml-0.5 flex-shrink-0 ${dotBg}`} />
            </div>
        )
    }

    return (
        <div className="py-1">
            <div className="flex items-center gap-1 px-2 mb-0.5">
                <div className="w-1 h-1 rounded-full bg-text-secondary" />
                <span className="section-header">WALL MIGRATION</span>
            </div>
            {renderRow('C', callHistory, callWall, true)}
            {renderRow('P', putHistory, putWall, false)}
        </div>
    )
}

import React from 'react'
import { fmtPrice } from '../../lib/utils'

interface PropTableRow {
    type_label: string
    type_bg: string
    type_text: string
    h1: number | null
    h2: number | null
    current: number | null
    dot_color: string
}

interface Props {
    rows: PropTableRow[]
}

export const WallMigration: React.FC<Props> = ({ rows }) => {
    return (
        <div className="p-2 pb-3 space-y-1">
            <div className="flex items-center gap-2 mb-1 pl-1">
                <div className="w-1 h-1 rounded-full bg-text-secondary" />
                <span className="section-header tracking-widest text-[#a1a1aa]">WALL MIGRATION</span>
            </div>

            <div className="flex flex-col gap-1 px-1">
                {rows.map((row, i) => (
                    <div key={i} className="flex items-center gap-0.5 h-7 px-1 py-0.5">
                        {/* Type label */}
                        <div className={`w-5 h-5 flex items-center justify-center rounded-sm text-2xs font-bold flex-shrink-0 ${row.type_text} bg-${row.type_bg}`}>
                            {row.type_label}
                        </div>

                        {/* History cell 1 */}
                        <div className="flex-1 flex items-center justify-center border border-bg-border bg-white/5 rounded-sm h-5">
                            <span className="mono text-2xs text-text-secondary">{row.h1 != null ? fmtPrice(row.h1) : '—'}</span>
                        </div>

                        {/* History cell 2 */}
                        <div className="flex-1 flex items-center justify-center border border-bg-border bg-white/5 rounded-sm h-5">
                            <span className="mono text-2xs text-text-secondary">{row.h2 != null ? fmtPrice(row.h2) : '—'}</span>
                        </div>

                        {/* Current — Highlighted Box */}
                        <div className="flex-1 flex items-center justify-center rounded-sm h-5"
                            style={{
                                border: '1px solid var(--wall-highlight-border)',
                                background: 'var(--wall-highlight-bg)',
                                boxShadow: '0 0 6px rgba(245, 158, 11, 0.25)'
                            }}>
                            <span className="mono text-2xs text-accent-amber font-bold">{row.current != null ? fmtPrice(row.current) : '—'}</span>
                        </div>

                        {/* Pulse dot matching Asian colors */}
                        <div className="ml-1 w-2.5 flex justify-center">
                            <div className={`w-2 h-2 rounded-full ${row.dot_color}`} />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

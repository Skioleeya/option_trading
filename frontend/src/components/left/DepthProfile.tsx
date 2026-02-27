import React from 'react'

interface PropTableRow {
    strike: number
    put_pct: number
    call_pct: number
    put_color: string
    call_color: string
    is_dominant_put: boolean
    is_dominant_call: boolean
    is_spot: boolean
    is_flip: boolean
    strike_color: string
}

interface Props {
    rows: PropTableRow[]
}

export const DepthProfile: React.FC<Props> = ({ rows }) => {
    return (
        <div className="flex flex-col flex-1 min-h-0 overflow-y-auto px-1 py-1 custom-scrollbar">
            <div className="flex flex-col gap-[2px]">
                {rows.map((row) => (
                    <div
                        key={row.strike}
                        className="flex items-center text-3xs h-[18px] hover:bg-white/5 cursor-pointer rounded-sm px-1 transition-colors relative"
                    >
                        {/* 1. Put Bar (Left Side) */}
                        <div className="flex-1 flex justify-end mr-1 relative h-full items-center">
                            <div
                                className={`h-[8px] rounded-sm transition-all duration-300 ${row.put_color} ${row.is_dominant_put ? 'opacity-100' : 'opacity-60'}`}
                                style={{ width: `${Math.max(row.put_pct * 100, 1)}%` }} // min 1% for visibility
                            />
                            {/* Put Label if dominant */}
                            {row.is_dominant_put && (
                                <span className={`absolute -left-1 text-[9px] font-bold text-market-down`}>
                                    P
                                </span>
                            )}
                        </div>

                        {/* 2. Center Strike Price */}
                        <div className={`w-[45px] text-center font-mono tracking-tighter ${row.strike_color} z-10 relative`}>
                            {row.strike.toFixed(0)}

                            {/* Spot Highlight Background */}
                            {row.is_spot && (
                                <div className="absolute inset-0 bg-white/5 border-y border-white/10 pointer-events-none" />
                            )}
                        </div>

                        {/* 3. Call Bar (Right Side) */}
                        <div className="flex-1 ml-1 relative h-full flex items-center">
                            <div
                                className={`h-[8px] rounded-sm transition-all duration-300 ${row.call_color} ${row.is_dominant_call ? 'opacity-100' : 'opacity-60'}`}
                                style={{ width: `${Math.max(row.call_pct * 100, 1)}%` }}
                            />
                            {/* Call Label if dominant */}
                            {row.is_dominant_call && (
                                <span className={`absolute -right-1 text-[9px] font-bold text-market-up`}>
                                    C
                                </span>
                            )}
                        </div>

                        {/* Overlay Tags for Flip / Spot */}
                        {row.is_flip && (
                            <span className="absolute right-1 text-[8px] tracking-wider font-bold text-accent-purple bg-accent-purple/10 px-0.5 rounded border border-accent-purple/20">
                                FLIP
                            </span>
                        )}
                        {row.is_spot && !row.is_flip && (
                            <span className="absolute right-1 text-[8px] tracking-wider font-bold text-accent-amber border border-accent-amber/30 bg-accent-amber/10 px-0.5 rounded">
                                SPOT
                            </span>
                        )}
                    </div>
                ))}
            </div>
        </div>
    )
}

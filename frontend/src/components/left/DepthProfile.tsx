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
    put_label_color: string      // Added
    call_label_color: string     // Added
    spot_tag_classes: string     // Added
    flip_tag_classes: string     // Added
}

interface Props {
    rows: PropTableRow[]
}

export const DepthProfile: React.FC<Props> = ({ rows }) => {
    return (
        <div className="flex flex-col flex-1 min-h-0 overflow-y-auto px-1 py-1 custom-scrollbar">
            <div className="flex flex-col gap-[2px]">
                {rows.map((row) => (
                    <div key={row.strike}>
                        {/* Row container */}
                        <div
                            className={`flex items-center text-3xs h-[18px] hover:bg-white/5 cursor-pointer rounded-sm px-1 transition-colors relative ${row.is_spot ? 'bg-white/5' : ''}`}
                        >
                            {/* 1. Put Bar (Left Side) */}
                            <div className="flex-1 flex justify-end mr-1 relative h-full items-center">
                                <div
                                    className={`h-[8px] rounded-sm transition-all duration-300 ${row.put_color} ${row.is_dominant_put ? 'opacity-100' : 'opacity-60'}`}
                                    style={{ width: `${Math.max(row.put_pct * 100, 1)}%` }} // min 1% for visibility
                                />
                                {/* Put Label if dominant */}
                                {row.is_dominant_put && (
                                    <span className={`absolute -left-1 text-[9px] font-bold ${row.put_label_color}`}>
                                        P
                                    </span>
                                )}
                            </div>

                            {/* 2. Center Strike Price */}
                            <div className="w-[45px] flex flex-col items-center justify-center relative h-full">
                                {/* Center vertical line */}
                                <div className="w-px bg-bg-border absolute left-1/2 -translate-x-1/2 h-full z-0" />

                                <span className={`font-mono tracking-tighter ${row.strike_color} z-10 relative px-1`}>
                                    {row.strike.toFixed(0)}
                                </span>
                            </div>

                            {/* 3. Call Bar (Right Side) */}
                            <div className="flex-1 ml-1 relative h-full flex items-center">
                                <div
                                    className={`h-[8px] rounded-sm transition-all duration-300 ${row.call_color} ${row.is_dominant_call ? 'opacity-100' : 'opacity-60'}`}
                                    style={{ width: `${Math.max(row.call_pct * 100, 1)}%` }}
                                />
                                {/* Call Label if dominant */}
                                {row.is_dominant_call && (
                                    <span className={`absolute -right-1 text-[9px] font-bold ${row.call_label_color}`}>
                                        C
                                    </span>
                                )}
                            </div>

                            {/* Overlay Tags for Flip / Spot */}
                            {row.is_spot && (
                                <span className={`absolute right-1 text-[8px] tracking-wider px-0.5 rounded ${row.spot_tag_classes}`}>
                                    SPOT
                                </span>
                            )}
                        </div>

                        {/* FLIP dashed line — drawn as separator below flip strike */}
                        {row.is_flip && (
                            <div className="flex items-center -mt-[1px] mb-[1px]">
                                <div className="flex-1" />
                                <div className="w-[45px]" />
                                <div className="flex-1 border-t border-dashed border-accent-purple/60 flex items-center">
                                    <span className="mono text-3xs text-accent-purple font-bold px-1 tracking-widest bg-bg-primary">FLIP</span>
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    )
}

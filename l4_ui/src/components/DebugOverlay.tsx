import React, { memo } from 'react'
import { useDashboardStore } from '../store/dashboardStore'
import { X, Activity, Database, Cpu } from 'lucide-react'

// Raw L1 data diagnostics overlay

interface Props {
    open: boolean
    onClose: () => void
}

export const DebugOverlay: React.FC<Props> = memo(({ open, onClose }) => {
    const payload = useDashboardStore(s => s.payload)
    const connStatus = useDashboardStore(s => s.connectionStatus)

    if (!open) return null

    const fused = payload?.agent_g?.data?.fused_signal
    const raw = {
        vpin: fused?.raw_vpin ?? 'N/A',
        bbo: fused?.raw_bbo_imb ?? 'N/A',
        volAccel: fused?.raw_vol_accel ?? 'N/A',
        asOf: payload?.timestamp ?? 'Syncing...'
    }

    return (
        <div className="fixed inset-0 z-[10000] flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/80 backdrop-blur-md"
                onClick={onClose}
            />

            {/* Terminal Window */}
            <div className="relative w-full max-w-4xl bg-[#09090b] border border-[#27272a] rounded-lg shadow-2xl overflow-hidden font-mono text-[11px] flex flex-col max-h-[85vh]">

                {/* Header */}
                <div className="flex items-center justify-between px-4 py-2 border-b border-[#27272a] bg-[#18181b]">
                    <div className="flex items-center gap-3">
                        <div className="flex gap-1.5">
                            <div className="w-2.5 h-2.5 rounded-full bg-[#ef4444]" onClick={onClose} />
                            <div className="w-2.5 h-2.5 rounded-full bg-[#f59e0b]" />
                            <div className="w-2.5 h-2.5 rounded-full bg-[#10b981]" />
                        </div>
                        <span className="text-[#a1a1aa] font-bold tracking-widest pl-2 border-l border-[#3f3f46]">L1 SIMD DIAGNOSTICS</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <span className={`${connStatus === 'connected' ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                            {connStatus.toUpperCase()}
                        </span>
                        <span className="text-[#52525b]">{raw.asOf}</span>
                        <button onClick={onClose} className="text-[#71717a] hover:text-white transition-colors">
                            <X size={14} />
                        </button>
                    </div>
                </div>

                {/* Content Matrix */}
                <div className="flex-1 overflow-auto p-4 custom-scrollbar">

                    {/* Hero Stats */}
                    <div className="grid grid-cols-3 gap-4 mb-6">
                        <div className="bg-[#18181b] border border-[#27272a] rounded p-3 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 p-2 opacity-10">
                                <Cpu size={40} />
                            </div>
                            <div className="text-[#52525b] font-bold mb-1">VPIN V2 (Rust SIMD)</div>
                            <div className="text-2xl text-[#e4e4e7]">{raw.vpin}</div>
                            <div className="text-[9px] text-[#71717a] mt-2">Volume-Synchronized Probability of Informed Trading</div>
                        </div>

                        <div className="bg-[#18181b] border border-[#27272a] rounded p-3 relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-2 opacity-10">
                                <Database size={40} />
                            </div>
                            <div className="text-[#52525b] font-bold mb-1">BBO Imbalance</div>
                            <div className="text-2xl text-[#e4e4e7]">{raw.bbo}</div>
                            <div className="text-[9px] text-[#71717a] mt-2">Bid-Ask spread pressure vector</div>
                        </div>

                        <div className="bg-[#18181b] border border-[#27272a] rounded p-3 relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-2 opacity-10">
                                <Activity size={40} />
                            </div>
                            <div className="text-[#52525b] font-bold mb-1">Volume Acceleration</div>
                            <div className="text-2xl text-[#e4e4e7]">{raw.volAccel}</div>
                            <div className="text-[9px] text-[#71717a] mt-2">Trade frequency delta vs 5m MA</div>
                        </div>
                    </div>

                    {/* Matrix Stream Log */}
                    <div className="border border-[#27272a] rounded bg-black h-[400px] p-0 flex flex-col">
                        <div className="px-3 py-1.5 border-b border-[#27272a] text-[#52525b] font-bold bg-[#09090b] sticky top-0">
                            RAW TELEMETRY STREAM
                        </div>
                        <div className="flex-1 overflow-auto p-3 text-[10px] leading-relaxed relative">
                            <pre className="text-[#71717a]">
                                {`[SYS] Initializing SIMD Matrix Decoder... OK
[SYS] Memory bounds aligned. Max Strikes: 512 (f32).
[STREAM] Listening to wss://localhost/ws/dashboard
--------------------------------------------------
`}
                                <span className="text-[#10b981]">{"{"}</span>
                                <span className="text-[#3b82f6]">"vpin_buffer"</span><span className="text-[#e4e4e7]">: {raw.vpin},</span>
                                <span className="text-[#3b82f6]">"bbo_bias"</span><span className="text-[#e4e4e7]">: {raw.bbo},</span>
                                <span className="text-[#3b82f6]">"accel_hz"</span><span className="text-[#e4e4e7]">: {raw.volAccel}</span>
                                <span className="text-[#10b981]">{"}"}</span>
                                {`
--------------------------------------------------
[INFO] UI payload dynamically routing L1 memory block.
[INFO] Awaiting next tick...`}
                            </pre>
                            {/* Scanning line effect */}
                            <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-[#10b981]/50 to-transparent animate-[scan_2s_linear_infinite]" />
                        </div>
                    </div>

                </div>
            </div>
        </div>
    )
})

DebugOverlay.displayName = 'DebugOverlay'

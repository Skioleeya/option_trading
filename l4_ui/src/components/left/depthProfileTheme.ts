/**
 * DepthProfile visual tokens.
 * Keep directional red/green styling centralized here.
 */
export const DEPTH_PROFILE_THEME = {
    putDominantBarClass:
        'bg-gradient-to-l from-[#059669] to-[#10b981] border-l border-[#34d399] shadow-[-2px_0_6px_rgba(16,185,129,0.3)]',
    putNormalBarClass:
        'bg-gradient-to-l from-[#064e3b] to-[#059669]/90 border-l border-[#10b981]/50',
    putMaxTagClass:
        'bg-[#022c22]/90 border-l border-[#10b981]/40 text-[#34d399]',
    putSpineLineClass:
        'bg-[#34d399] shadow-[0_0_4px_rgba(52,211,153,0.8)]',

    callDominantBarClass:
        'bg-gradient-to-r from-[#dc2626] to-[#ef4444] border-r border-[#f87171] shadow-[2px_0_6px_rgba(239,68,68,0.3)]',
    callNormalBarClass:
        'bg-gradient-to-r from-[#7f1d1d] to-[#dc2626]/90 border-r border-[#ef4444]/50',
    callMaxTagClass:
        'bg-[#450a0a]/90 border-r border-[#ef4444]/40 text-[#f87171]',
    callSpineLineClass:
        'bg-[#f87171] shadow-[0_0_4px_rgba(248,113,113,0.8)]',
} as const


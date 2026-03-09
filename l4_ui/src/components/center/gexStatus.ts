export interface GexStatusInput {
    netGex: number | null | undefined
    callWall: number | null | undefined
    flipLevel: number | null | undefined
    putWall: number | null | undefined
}

export interface GexStatusNormalized {
    netGex: number | null
    callWall: number | null
    flipLevel: number | null
    putWall: number | null
}

export type GexDirection = 'BULLISH' | 'BEARISH' | 'NEUTRAL'

export interface AsianGexTone {
    direction: GexDirection
    textClass: string
}

export const ASIAN_WALL_STYLE = {
    // Asian style: bearish/ceiling pressure uses green
    call: 'bg-[#022c22] border border-[#065f46]/60 text-[#10b981]',
    // Asian style: bullish/support pressure uses red
    put: 'bg-[#450a0a] border border-[#7f1d1d]/60 text-[#ef4444]',
    flip: 'bg-[#422006] border border-[#92400e]/60 text-[#f59e0b]',
} as const

function finiteOrNull(val: number | null | undefined): number | null {
    if (typeof val !== 'number' || !Number.isFinite(val)) return null
    return val
}

// Strike-like levels <= 0 are invalid in SPY options context and should render as unavailable.
export function sanitizeLevelPrice(val: number | null | undefined): number | null {
    const n = finiteOrNull(val)
    if (n === null || n <= 0) return null
    return n
}

export function normalizeGexStatus(input: GexStatusInput): GexStatusNormalized {
    return {
        netGex: finiteOrNull(input.netGex),
        callWall: sanitizeLevelPrice(input.callWall),
        flipLevel: sanitizeLevelPrice(input.flipLevel),
        putWall: sanitizeLevelPrice(input.putWall),
    }
}

export function resolveAsianGexTone(netGex: number | null | undefined): AsianGexTone {
    const n = finiteOrNull(netGex)
    if (n === null || n === 0) {
        return { direction: 'NEUTRAL', textClass: 'text-[#71717a]' }
    }
    if (n > 0) {
        return { direction: 'BULLISH', textClass: 'text-[#ef4444]' }
    }
    return { direction: 'BEARISH', textClass: 'text-[#10b981]' }
}

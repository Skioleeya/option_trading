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
    // Asian style: CALL uses red
    call: 'bg-wall-call border border-market-up/60 text-market-up',
    // Asian style: PUT uses green
    put: 'bg-wall-put border border-market-down/60 text-market-down',
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
        return { direction: 'NEUTRAL', textClass: 'text-text-secondary' }
    }
    if (n > 0) {
        return { direction: 'BULLISH', textClass: 'text-market-up' }
    }
    return { direction: 'BEARISH', textClass: 'text-market-down' }
}

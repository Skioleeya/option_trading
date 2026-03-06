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

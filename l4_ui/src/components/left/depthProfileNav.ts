export type DepthProfileNavEvent =
    | 'l4:nav_spot'
    | 'l4:nav_call_wall'
    | 'l4:nav_put_wall'
    | 'l4:nav_flip'

export interface DepthProfileNavContext {
    eventType: DepthProfileNavEvent
    spot: number | null
    currentSpotStrike: number | null
    callWall: number | null
    putWall: number | null
    flipLevel: number | null
}

export function resolveNavigationTarget(ctx: DepthProfileNavContext): number | null {
    if (ctx.eventType === 'l4:nav_spot') {
        return finiteOrNull(ctx.spot ?? ctx.currentSpotStrike)
    }
    if (ctx.eventType === 'l4:nav_call_wall') {
        return finiteOrNull(ctx.callWall)
    }
    if (ctx.eventType === 'l4:nav_put_wall') {
        return finiteOrNull(ctx.putWall)
    }
    if (ctx.eventType === 'l4:nav_flip') {
        return finiteOrNull(ctx.flipLevel)
    }
    return null
}

export function resolveNearestStrike(
    target: number | null,
    strikes: number[],
): number | null {
    if (target == null || !Number.isFinite(target) || strikes.length === 0) {
        return null
    }

    let nearest: number | null = null
    let nearestDistance = Number.POSITIVE_INFINITY
    for (const strike of strikes) {
        if (!Number.isFinite(strike)) {
            continue
        }
        const distance = Math.abs(strike - target)
        if (distance < nearestDistance) {
            nearest = strike
            nearestDistance = distance
        }
    }
    return nearest
}

function finiteOrNull(value: number | null | undefined): number | null {
    if (value == null || !Number.isFinite(value)) {
        return null
    }
    return value
}

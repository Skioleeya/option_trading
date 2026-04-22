import type { DashboardPayload } from '../types/dashboard'
import { getPayloadTradeDateKey } from './dashboardStore.helpers'

const STICKY_KEYS = [
    'wall_migration',
    'depth_profile',
    'tactical_triad',
    'skew_dynamics',
    'macro_volume_map',
] as const

type StickyKey = (typeof STICKY_KEYS)[number]
const EXPLICIT_CLEAR_ARRAY_KEYS = new Set<StickyKey>(['wall_migration', 'depth_profile'])

function isEmpty(val: unknown): boolean {
    if (val === null || val === undefined) return true
    if (Array.isArray(val)) return val.length === 0
    if (typeof val === 'object') return Object.keys(val as object).length === 0
    return false
}

export function smartMergeUiState(prev: any, next: any): any {
    const merged = { ...prev, ...next }
    for (const key of STICKY_KEYS as readonly StickyKey[]) {
        const newVal = next?.[key]
        const oldVal = prev?.[key]
        // For wall/depth arrays, [] means explicit clear from backend.
        if (
            EXPLICIT_CLEAR_ARRAY_KEYS.has(key)
            && Array.isArray(newVal)
            && newVal.length === 0
        ) {
            continue
        }
        // Missing/null keeps previous sticky value to protect partial delta payloads.
        if ((newVal === null || newVal === undefined) && !isEmpty(oldVal)) {
            merged[key] = oldVal
            continue
        }
        if (isEmpty(newVal) && !isEmpty(oldVal)) {
            merged[key] = oldVal
        }
    }
    return merged
}

export function mergePayloads(
    prev: DashboardPayload | null,
    next: DashboardPayload
): DashboardPayload {
    if (!prev) return next
    const prevUiState = prev.agent_g?.data?.ui_state ?? {}
    const nextUiState = next.agent_g?.data?.ui_state ?? {}
    const prevTradeDate = getPayloadTradeDateKey(prev)
    const nextTradeDate = getPayloadTradeDateKey(next)
    const allowStickyMerge =
        prevTradeDate === null
        || nextTradeDate === null
        || prevTradeDate === nextTradeDate
    const mergedUiState = allowStickyMerge
        ? smartMergeUiState(prevUiState, nextUiState)
        : nextUiState

    return {
        ...prev,
        ...next,
        agent_g: next.agent_g
            ? {
                ...next.agent_g,
                data: {
                    ...(next.agent_g.data ?? {}),
                    ui_state: mergedUiState,
                },
            }
            : prev.agent_g,
    } as DashboardPayload
}

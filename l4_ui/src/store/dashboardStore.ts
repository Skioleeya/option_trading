/**
 * l4_ui — DashboardStore (Phase 1: State Decoupling)
 * ─────────────────────────────────────────────────────────
 * Zustand store with subscribeWithSelector middleware.
 *
 * Replaces scattered useState in useDashboardWS.ts with a single
 * immutable state tree. Each UI component subscribes only to its own
 * slice, eliminating full-tree re-renders on every WS message.
 *
 * Backwards compatibility:
 *   useDashboardWS() continues to export { status, payload, sendPing }.
 */

import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import type {
    DashboardPayload,
    ConnectionStatus,
    AtmDecay,
    HeaderVolatilityContext,
} from '../types/dashboard'
import {
    appendAtmHistoryTick,
    extractAtm,
    extractHeaderVolatility,
    extractIvPct,
    extractSpot,
    getEtTradeDateKeyFromTimestamp,
    getPayloadTradeDateKey,
    keepHistoryWithinTradeDate,
    MAX_ATM_HISTORY,
} from './dashboardStore.helpers'
import { mergePayloads } from './dashboardStore.merge'

export interface DashboardState {
    connectionStatus: ConnectionStatus
    payload: DashboardPayload | null
    spot: number | null
    ivPct: number | null
    headerVolatility: HeaderVolatilityContext | null
    payloadVersion: number | null
    broadcastTimestamp: string | null
    driftMs: number | null
    driftWarning: boolean | null
    isStale: boolean | null
    version: number
    atm: AtmDecay | null
    atmHistory: AtmDecay[]
    atmHistoryTradeDateKey: string | null
    atmHistoryLastTimestamp: string | null
    setConnectionStatus: (status: ConnectionStatus) => void
    applyFullUpdate: (payload: DashboardPayload) => void
    applyMergedPayload: (next: DashboardPayload) => void
    appendAtmHistory: (tick: AtmDecay) => void
    hydrateAtmHistory: (history: AtmDecay[]) => void
}

function resolveLiveHistoryBase(
    state: DashboardState,
    tradeDateKey: string | null,
): AtmDecay[] {
    if (tradeDateKey === null) {
        return state.atmHistory
    }
    return state.atmHistoryTradeDateKey === tradeDateKey
        ? state.atmHistory
        : []
}

function appendLiveAtmTick(
    state: DashboardState,
    tradeDateKey: string | null,
    atm: AtmDecay | null,
): {
    atmHistory: AtmDecay[]
    atmHistoryTradeDateKey: string | null
    atmHistoryLastTimestamp: string | null
} {
    const baseHistory = resolveLiveHistoryBase(state, tradeDateKey)
    let nextHistory = baseHistory
    let nextLastTimestamp = baseHistory[baseHistory.length - 1]?.timestamp ?? null

    if (
        atm?.timestamp
        && atm.timestamp !== nextLastTimestamp
        && !baseHistory.some((entry) => entry.timestamp === atm.timestamp)
    ) {
        nextHistory = appendAtmHistoryTick(baseHistory, atm)
        nextLastTimestamp = atm.timestamp
    }

    return {
        atmHistory: nextHistory,
        atmHistoryTradeDateKey: tradeDateKey,
        atmHistoryLastTimestamp: nextLastTimestamp,
    }
}

export const useDashboardStore = create<DashboardState>()(
    subscribeWithSelector((set, get) => ({
        connectionStatus: 'connecting',
        payload: null,
        spot: null,
        ivPct: null,
        headerVolatility: null,
        payloadVersion: null,
        broadcastTimestamp: null,
        driftMs: null,
        driftWarning: null,
        isStale: null,
        atm: null,
        atmHistory: [],
        atmHistoryTradeDateKey: null,
        atmHistoryLastTimestamp: null,
        version: 0,

        setConnectionStatus: (status) => set({ connectionStatus: status }),

        applyFullUpdate: (incoming) => {
            const prev = get().payload
            const merged = mergePayloads(prev, incoming)
            const atm = extractAtm(merged)

            if (atm === null && get().atm !== null) {
                console.warn('[L4 Debug] ATM becoming NULL in applyFullUpdate. Prev:', get().atm, 'Incoming:', incoming)
            }

            set((state) => {
                const tradeDateKey = getPayloadTradeDateKey(merged)
                const nextHistoryState = appendLiveAtmTick(state, tradeDateKey, atm)

                return {
                    payload: merged,
                    spot: extractSpot(merged),
                    ivPct: extractIvPct(merged),
                    headerVolatility: extractHeaderVolatility(merged),
                    payloadVersion: merged.version ?? null,
                    broadcastTimestamp: merged.broadcast_timestamp ?? null,
                    driftMs: merged.drift_ms ?? null,
                    driftWarning: merged.drift_warning ?? null,
                    isStale: merged.is_stale ?? null,
                    atm,
                    ...nextHistoryState,
                    version: state.version + 1,
                }
            })
        },

        applyMergedPayload: (next) => {
            const prev = get().payload
            const merged = mergePayloads(prev, next)
            const atm = extractAtm(merged)

            if (atm === null && get().atm !== null) {
                console.warn('[L4 Debug] ATM becoming NULL in applyMergedPayload. Prev:', get().atm, 'Incoming:', next)
            }

            set((state) => {
                const tradeDateKey = getPayloadTradeDateKey(merged)
                const nextHistoryState = appendLiveAtmTick(state, tradeDateKey, atm)

                return {
                    payload: merged,
                    spot: extractSpot(merged),
                    ivPct: extractIvPct(merged),
                    headerVolatility: extractHeaderVolatility(merged),
                    payloadVersion: merged.version ?? null,
                    broadcastTimestamp: merged.broadcast_timestamp ?? null,
                    driftMs: merged.drift_ms ?? null,
                    driftWarning: merged.drift_warning ?? null,
                    isStale: merged.is_stale ?? null,
                    atm,
                    ...nextHistoryState,
                    version: state.version + 1,
                }
            })
        },

        appendAtmHistory: (tick) => {
            set((state) => {
                const tickTradeDate = getEtTradeDateKeyFromTimestamp(tick.timestamp ?? null)
                const baseHistory = resolveLiveHistoryBase(state, tickTradeDate)
                if (tick.timestamp && baseHistory.some((entry) => entry.timestamp === tick.timestamp)) {
                    return state
                }
                return {
                    atmHistory: appendAtmHistoryTick(baseHistory, tick),
                    atmHistoryTradeDateKey: tickTradeDate,
                    atmHistoryLastTimestamp: tick.timestamp ?? baseHistory[baseHistory.length - 1]?.timestamp ?? null,
                }
            })
        },

        hydrateAtmHistory: (history) => {
            set((state) => {
                const activeTradeDate =
                    getPayloadTradeDateKey(state.payload)
                    ?? getEtTradeDateKeyFromTimestamp(history[history.length - 1]?.timestamp ?? null)
                const baseHistory = resolveLiveHistoryBase(state, activeTradeDate)
                const scopedIncoming = activeTradeDate
                    ? keepHistoryWithinTradeDate(history, activeTradeDate)
                    : history
                const existingTimestamps = new Set(baseHistory.map((tick) => tick.timestamp))
                const newPoints = scopedIncoming.filter((tick) => tick.timestamp && !existingTimestamps.has(tick.timestamp))

                if (newPoints.length === 0) return state

                const combined = [...baseHistory, ...newPoints].sort((a, b) =>
                    (a.timestamp || '').localeCompare(b.timestamp || '')
                )
                const nextHistory = combined.slice(-MAX_ATM_HISTORY)

                return {
                    atmHistory: nextHistory,
                    atmHistoryTradeDateKey: activeTradeDate,
                    atmHistoryLastTimestamp: nextHistory[nextHistory.length - 1]?.timestamp ?? null,
                }
            })
        },
    }))
)

export { smartMergeUiState } from './dashboardStore.merge'
export * from './dashboardStore.selectors'

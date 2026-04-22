import type {
    DashboardPayload,
    AtmDecay,
    HeaderVolatilityContext,
} from '../types/dashboard'

// Keep one full regular session (09:30-16:00 ET) with headroom for sub-second bursts.
export const MAX_ATM_HISTORY = 30000

const ET_TIME_ZONE = 'America/New_York'
const ET_TRADE_DATE_FORMATTER = new Intl.DateTimeFormat('en-CA', {
    timeZone: ET_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
})

function toValidDate(raw: string | null | undefined): Date | null {
    if (!raw) return null
    const d = new Date(raw)
    if (Number.isNaN(d.getTime())) return null
    return d
}

export function getEtTradeDateKeyFromTimestamp(raw: string | null | undefined): string | null {
    const d = toValidDate(raw)
    if (!d) return null
    return ET_TRADE_DATE_FORMATTER.format(d)
}

export function getPayloadTradeDateKey(payload: DashboardPayload | null | undefined): string | null {
    if (!payload) return null
    const sourceTs =
        payload.data_timestamp
        ?? payload.timestamp
        ?? payload.agent_g?.as_of
        ?? null
    return getEtTradeDateKeyFromTimestamp(sourceTs)
}

export function keepHistoryWithinTradeDate(history: AtmDecay[], tradeDateKey: string | null): AtmDecay[] {
    if (!tradeDateKey) return history
    return history.filter((tick) => getEtTradeDateKeyFromTimestamp(tick.timestamp ?? null) === tradeDateKey)
}

export function appendAtmHistoryTick(history: AtmDecay[], tick: AtmDecay): AtmDecay[] {
    return [...history.slice(-MAX_ATM_HISTORY + 1), tick]
}

export function extractSpot(p: DashboardPayload): number | null {
    return p?.spot ?? null
}

export function extractIvPct(p: DashboardPayload): number | null {
    return p?.agent_g?.data?.spy_atm_iv ?? null
}

export function extractHeaderVolatility(p: DashboardPayload): HeaderVolatilityContext | null {
    return p?.agent_g?.data?.header_volatility ?? null
}

export function extractAtm(p: DashboardPayload): AtmDecay | null {
    return p?.atm ?? p?.agent_g?.data?.ui_state?.atm ?? null
}

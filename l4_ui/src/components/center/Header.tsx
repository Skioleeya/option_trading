/**
 * Header — Zustand field-level selectors with grouped center-lane layout.
 */
import React, { memo, useEffect, useRef, useState } from 'react'
import { fmtPrice } from '../../lib/utils'
import type { ConnectionStatus, HeaderVolatilityContext } from '../../types/dashboard'
import {
    useDashboardStore,
    selectSpot,
    selectIvPct,
    selectHeaderVolatility,
    selectConnectionStatus,
    selectPayloadTimestamp,
    selectFusedIvRegime,
    selectUiStateIvVelocity,
    selectRustActive,
} from '../../store/dashboardStore'
import {
    deriveMarketStatus,
    getConnectionDotClass,
    getConnectionLabel,
    getRustIndicator,
} from './headerState'

interface Props {
    spot?: number | null
    ivPct?: number | null
    ivRegime?: string
    status?: ConnectionStatus
    marketStatus?: string
    as_of?: string | null
}

type SpotTickDirection = 'neutral' | 'up' | 'down'

function formatTokenValue(value: number | null | undefined, digits = 0): string {
    if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
    return value.toFixed(digits)
}

function formatRatio(value: number | null | undefined): string {
    if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
    return value.toFixed(2)
}

function relationBadgeState(context: HeaderVolatilityContext | null): string {
    const state = context?.iv_price_relation?.state
    if (!state || state === 'UNAVAILABLE') return '—'
    if (state === 'INVERSE_CONFIRM') return 'INV'
    if (state === 'POSITIVE_DIVERGENCE') return 'POS'
    if (state === 'VOL_LEAD') return 'VOL'
    if (state === 'PRICE_LEAD') return 'PX'
    return state
}

function termTokenClass(state: string | undefined): string {
    if (state === 'INVERTED') return 'text-[#ef4444]'
    if (state === 'FLAT') return 'text-[#f59e0b]'
    if (state === 'NORMAL') return 'text-[#10b981]'
    return 'text-[#71717a]'
}

function velocityText(state: string | null | undefined): string | null {
    if (!state) return null
    if (state.includes('EXPANSION') || state.includes('MOVE')) return `UP ${state}`
    if (state.includes('DROP')) return `DOWN ${state}`
    return state
}

function Divider(): React.JSX.Element {
    return <i className="l4-header__divider" aria-hidden="true" />
}

export const Header: React.FC<Props> = memo(({
    spot: propSpot,
    ivPct: propIvPct,
    ivRegime: propIvRegime,
    status: propStatus,
    marketStatus: propMarketStatus,
    as_of: propAsOf,
}) => {
    // Field-level selectors
    const storeSpot = useDashboardStore(selectSpot)
    const storeIvPct = useDashboardStore(selectIvPct)
    const storeStatus = useDashboardStore(selectConnectionStatus)
    const timestamp = useDashboardStore(selectPayloadTimestamp)
    const ivRegimeRaw = useDashboardStore(selectFusedIvRegime)
    const storeIvVelocity = useDashboardStore(selectUiStateIvVelocity)
    const headerVolatility = useDashboardStore(selectHeaderVolatility)

    const spot = storeSpot ?? propSpot ?? null
    const ivPct = storeIvPct ?? propIvPct ?? null
    const status = storeStatus ?? propStatus ?? 'connecting'
    const as_of = timestamp ?? propAsOf ?? null
    const ivRegime = ivRegimeRaw ?? propIvRegime ?? 'NORMAL'
    const marketStatus = propMarketStatus ?? deriveMarketStatus()
    const rustActive = useDashboardStore(selectRustActive)

    const timeStr = as_of
        ? new Date(as_of).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'America/New_York' })
        : '--:--:--'

    const connColor = getConnectionDotClass(status)
    const connLabel = getConnectionLabel(status)
    const rust = getRustIndicator(rustActive)
    const ivRegimeColor = (ivRegime === 'HIGH' || ivRegime === 'EXTREME') ? 'text-[#ef4444]' : ivRegime === 'ELEVATED' ? 'text-[#f59e0b]' : 'text-[#10b981]'
    const ivBadgeCls = (ivRegime === 'HIGH' || ivRegime === 'EXTREME') ? 'border-[#7f1d1d] text-[#ef4444] bg-[#450a0a]/50' : ivRegime === 'ELEVATED' ? 'border-[#92400e] text-[#f59e0b] bg-[#422006]/50' : 'border-[#065f46] text-[#10b981] bg-[#022c22]/50'
    const ivVelocityText = velocityText(storeIvVelocity?.state)
    const prevSpotRef = useRef<number | null>(null)
    const tickResetRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const [spotTickDirection, setSpotTickDirection] = useState<SpotTickDirection>('neutral')
    const [spotTickFlash, setSpotTickFlash] = useState<'up' | 'down' | null>(null)

    useEffect(() => {
        return () => {
            if (tickResetRef.current) {
                clearTimeout(tickResetRef.current)
            }
        }
    }, [])

    useEffect(() => {
        if (typeof spot !== 'number' || !Number.isFinite(spot)) {
            prevSpotRef.current = null
            setSpotTickDirection('neutral')
            setSpotTickFlash(null)
            if (tickResetRef.current) {
                clearTimeout(tickResetRef.current)
                tickResetRef.current = null
            }
            return
        }

        if (prevSpotRef.current === null) {
            prevSpotRef.current = spot
            setSpotTickDirection('neutral')
            setSpotTickFlash(null)
            return
        }

        if (spot > prevSpotRef.current) {
            setSpotTickDirection('up')
            setSpotTickFlash('up')
        } else if (spot < prevSpotRef.current) {
            setSpotTickDirection('down')
            setSpotTickFlash('down')
        } else {
            return
        }

        prevSpotRef.current = spot
        if (tickResetRef.current) {
            clearTimeout(tickResetRef.current)
        }
        tickResetRef.current = setTimeout(() => {
            setSpotTickFlash(null)
            tickResetRef.current = null
        }, 360)
    }, [spot])

    const spotTickClass =
        spotTickDirection === 'up'
            ? 'l4-header__spot-value--up'
            : spotTickDirection === 'down'
                ? 'l4-header__spot-value--down'
                : 'l4-header__spot-value--neutral'

    const spotTickFlashClass =
        spotTickFlash === 'up'
            ? 'l4-header__spot-value--tick-up'
            : spotTickFlash === 'down'
                ? 'l4-header__spot-value--tick-down'
                : ''

    return (
        <header className="l4-header font-sans selection:bg-transparent">
            <div className="l4-header__left">
                <span className="l4-header__left-title">ANALYSIS</span>
            </div>

            <div className="l4-header__center" data-testid="header-center">
                <div className="l4-header__center-shell" data-testid="header-center-shell">
                    <div className="l4-header__group-left l4-header__core" data-testid="header-group-left">
                        <span className="l4-header__brand">SPX SENTINEL</span>
                        <Divider />
                        <span className="l4-header__time">{timeStr} ET</span>
                        <Divider />
                        <span className={`l4-header__status ${marketStatus === 'OPEN' ? 'text-[#10b981]' : 'text-[#52525b]'}`}>{marketStatus}</span>
                        <Divider />
                        <div className="l4-header__spot-cluster">
                            <span className="l4-header__spot-label">SPY</span>
                            <span
                                className={`l4-header__spot-value ${spotTickClass} ${spotTickFlashClass}`.trim()}
                                data-testid="header-spot-value"
                            >
                                {fmtPrice(spot)}
                            </span>
                        </div>
                    </div>

                    <div className="l4-header__group-middle" data-testid="header-group-middle">
                        <div className="l4-header__iv-summary" data-testid="header-iv-summary">
                            <span className="l4-header__iv-label">IV</span>
                            <span className={`l4-header__iv-value ${ivRegimeColor}`}>{ivPct != null ? `${(ivPct * 100).toFixed(2)}%` : '—'}</span>
                        </div>

                        <div className="l4-header__detail-badge-wrap" data-testid="header-detail-badge-wrap">
                            <div className={`l4-header__vol-badge ${ivBadgeCls}`} data-testid="header-vol-badge">
                                <span className="l4-header__vol-state">{ivRegime}</span>
                                {ivVelocityText && (
                                    <span className={`l4-header__vol-velocity ${storeIvVelocity?.state?.includes('EXPANSION') || storeIvVelocity?.state?.includes('MOVE') ? 'text-[#ef4444]' : storeIvVelocity?.state?.includes('DROP') ? 'text-[#10b981]' : 'text-text-muted'}`}>
                                        {ivVelocityText}
                                    </span>
                                )}
                                <div className="l4-header__vol-micro" data-testid="header-vol-micro">
                                    <span className="l4-header__micro-token">R{formatTokenValue(headerVolatility?.ivr, 0)}</span>
                                    <span className="l4-header__micro-token">P{formatTokenValue(headerVolatility?.ivp, 0)}</span>
                                    <span className={`l4-header__micro-token ${termTokenClass(headerVolatility?.term_structure?.primary?.state)}`}>
                                        1D {formatRatio(headerVolatility?.term_structure?.primary?.ratio)}
                                    </span>
                                    <span className="l4-header__micro-token">VX {formatRatio(headerVolatility?.term_structure?.secondary?.ratio)}</span>
                                    <span className="l4-header__micro-token">β {relationBadgeState(headerVolatility)}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="l4-header__group-right l4-header__transport" data-testid="header-group-right">
                        <span className={`l4-header__rds-dot ${connColor}`} />
                        <span className="l4-header__rds-label">{connLabel}</span>
                    </div>
                </div>
            </div>

            <div className="l4-header__right">
                <span className="l4-header__offense-title l4-header__right-title">TACTICAL OFFENSIVE</span>
                <div className="l4-header__ops-cluster">
                    <span className="l4-header__rust">{rust.label}</span>
                    <span className={`l4-header__rust-dot ${rust.dotClass}`} />
                </div>
            </div>
        </header>
    )
})

Header.displayName = 'Header'

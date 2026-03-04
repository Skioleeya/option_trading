import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs))
}

/** Format a number as Millions or Billions string */
export function fmtGex(val: number | null | undefined): string {
    if (val == null) return '—'
    const abs = Math.abs(val)
    if (abs >= 1000) return `${(val / 1000).toFixed(2)}B`
    return `${val.toFixed(2)}M`
}

export function fmtPct(val: number | null | undefined, decimals = 1): string {
    if (val == null) return '—'
    return `${val > 0 ? '+' : ''}${(val * 100).toFixed(decimals)}%`
}

export function fmtPrice(val: number | null | undefined): string {
    if (val == null) return '—'
    return val.toFixed(2)
}

export function fmtVolume(val: number | null | undefined): string {
    if (val == null) return '—'
    if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`
    if (val >= 1_000) return `${(val / 1_000).toFixed(0)}K`
    return `${val}`
}

export function fmtFlow(val: number | null | undefined): string {
    if (val == null) return '—'
    const abs = Math.abs(val)
    const sign = val < 0 ? '-' : '+'
    if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(1)}M`
    if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(0)}K`
    return `${sign}$${abs}`
}

/** Return badge variant class for GEX regime */
export function gexRegimeBadge(regime: string): string {
    switch (regime) {
        case 'SUPER_PIN': return 'badge-amber'
        case 'DAMPING': return 'badge-green'
        case 'ACCELERATION': return 'badge-hollow-purple'
        default: return 'badge-neutral'
    }
}

/** Return badge label for GEX regime */
export function gexRegimeLabel(regime: string): string {
    switch (regime) {
        case 'SUPER_PIN': return 'SUPER PIN'
        case 'DAMPING': return 'DAMPING'
        case 'ACCELERATION': return 'VOLATILE'
        default: return 'NEUTRAL'
    }
}

/** Color for IV velocity state (红涨绿跌) */
export function ivStateColor(state: string): string {
    // Bearish-indicating states get green, bullish get red (Asian convention)
    switch (state) {
        case 'PAID_DROP': return 'text-accent-green'
        case 'PAID_MOVE':
        case 'ORGANIC_GRIND':
        case 'HOLLOW_RISE':
        case 'HOLLOW_DROP':
        case 'VOL_EXPANSION': return 'text-accent-red'
        case 'EXHAUSTION': return 'text-accent-amber'
        default: return 'text-text-secondary'
    }
}

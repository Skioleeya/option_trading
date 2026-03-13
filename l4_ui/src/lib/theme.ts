/**
 * Frontend Theme & Color Management API
 * -------------------------------------
 * Single source of truth for programmatic color access.
 * Sub-modules (TradingView Canvas, Recharts) should import these variables 
 * instead of hardcoding hex colors, ensuring consistency with the Asian Dragon style.
 */

const ASIAN_MARKET_UP = '#ef4444'
const ASIAN_MARKET_DOWN = '#10b981'
const ASIAN_MARKET_NEUTRAL = '#71717a'

export const THEME = {
    // Global Market Colors (Asian Dragon Standard)
    market: {
        up: ASIAN_MARKET_UP,        // Red -> Call / Price Up
        down: ASIAN_MARKET_DOWN,    // Green -> Put / Price Down
        neutral: ASIAN_MARKET_NEUTRAL,   // Zinc -> Neutral / Stable
    },

    // Base Layout
    bg: {
        primary: '#0a0a0a',
        card: '#161616',
        border: '#222222',
    },

    // Typography
    text: {
        primary: '#e4e4e7',
        secondary: '#71717a',
        muted: '#3f3f46',
    },

    // Semantic UI Accents (Badges, Statuses)
    accent: {
        // Keep accent red/green aligned with market semantics to avoid drift.
        green: ASIAN_MARKET_DOWN,
        red: ASIAN_MARKET_UP,
        amber: '#f59e0b',     // Warning / Siege / Spot Price / Super Pin
        purple: '#a855f7',    // Flip levels / Volatile
        cyan: '#06b6d4',      // Compression / Grind Stable
        blue: '#3b82f6',      // General Info
    },

    // ---------------------------------------------------------
    // Sub-module Specific UI Bindings
    // ---------------------------------------------------------

    // 1. Defense Area (Left Panel)
    defense: {
        depthProfile: {
            callBar: ASIAN_MARKET_UP,
            putBar: ASIAN_MARKET_DOWN,
            spotHighlightBg: 'rgba(255, 255, 255, 0.05)',
            flipLine: '#a855f7',
        },
        wallMigration: {
            callLabelBg: '#2a1318',     /* Deep red */
            putLabelBg: '#0f2115',      /* Deep green */
            currentValBorder: 'rgba(245, 158, 11, 0.7)',  /* Glowing Amber */
            currentValBg: 'rgba(245, 158, 11, 0.08)',
        },
        microStats: {
            panelBg: '#0a0c10',
            cardBorder: '#1e2025',
            cardBg: '#111318',
            cardHoverBg: '#15181e',
            title: '#8f939c',
            edgeIdle: 'rgba(255,255,255,0.05)',
            edgeHover: 'rgba(255,255,255,0.20)',
            iconNetGex: '#a855f7',
            iconWallDyn: '#f59e0b',
            iconMomentum: 'rgba(255,255,255,0.60)',
            iconVanna: '#06b6d4',
        }
    },

    // 2. Main Chart (TradingView Canvas)
    chart: {
        background: '#0a0a0a',
        gridLines: '#222222',
        crosshair: '#71717a',
        watermark: 'rgba(255,255,255, 0.03)',
        candlestick: {
            upColor: ASIAN_MARKET_UP,      // Asian Red
            downColor: ASIAN_MARKET_DOWN,    // Asian Green
            borderUpColor: ASIAN_MARKET_UP,
            borderDownColor: ASIAN_MARKET_DOWN,
            wickUpColor: ASIAN_MARKET_UP,
            wickDownColor: ASIAN_MARKET_DOWN,
        }
    }
} as const;

export type AppTheme = typeof THEME;

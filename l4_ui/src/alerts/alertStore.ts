/**
 * l4_ui — Alert Store (Phase 4)
 * ─────────────────────────────────────
 * Zustand store for in-app toast notifications.
 * Consumed by AlertToast component to render the notification queue.
 *
 * Design:
 *   • Capped ring-buffer: max 8 toasts (oldest auto-evicted)
 *   • Auto-dismiss: each toast expires after `ttlMs` (default 5s)
 *   • dismiss(id): manual dismiss
 *   • clearAll(): clear entire queue
 */

import { create } from 'zustand'
import type { L4Alert } from './types'

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ToastItem extends L4Alert {
    ttlMs: number
    expireAt: number
}

interface AlertStoreState {
    toasts: ToastItem[]
    push: (alert: L4Alert, ttlMs?: number) => void
    dismiss: (id: string) => void
    clearAll: () => void
    /** Prune expired toasts (called by toast renderer on each tick). */
    prune: () => void
}

// ─────────────────────────────────────────────────────────────────────────────
// TTL per severity
// ─────────────────────────────────────────────────────────────────────────────

const DEFAULT_TTL: Record<string, number> = {
    critical: 12_000,
    warning: 7_000,
    info: 4_000,
}

const MAX_TOASTS = 8

// ─────────────────────────────────────────────────────────────────────────────
// Store
// ─────────────────────────────────────────────────────────────────────────────

export const useAlertStore = create<AlertStoreState>((set, get) => ({
    toasts: [],

    push: (alert, ttlMs) => {
        const ttl = ttlMs ?? DEFAULT_TTL[alert.severity] ?? 5_000
        const toast: ToastItem = { ...alert, ttlMs: ttl, expireAt: Date.now() + ttl }

        set((s) => {
            // Deduplicate by alert id (idempotent push)
            const without = s.toasts.filter((t) => t.id !== toast.id)
            // Ring-buffer cap: take newest MAX_TOASTS-1 + new one
            const capped = without.slice(-(MAX_TOASTS - 1))
            return { toasts: [...capped, toast] }
        })

        // Schedule auto-dismiss
        setTimeout(() => {
            get().dismiss(alert.id)
        }, ttl)
    },

    dismiss: (id) => {
        set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
    },

    clearAll: () => set({ toasts: [] }),

    prune: () => {
        const now = Date.now()
        set((s) => ({ toasts: s.toasts.filter((t) => t.expireAt > now) }))
    },
}))

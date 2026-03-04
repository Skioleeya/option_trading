/**
 * l4_ui — Alert Toast Renderer (Phase 4)
 * ─────────────────────────────────────────────
 * Subscribes to alertStore and renders a fixed-position toast stack.
 * Positioned: bottom-right, above the GEX status bar.
 *
 * Features:
 *   • Severity-coded border + icon (critical=red, warning=amber, info=blue)
 *   • Animated slide-in/out via CSS transition
 *   • Click-to-dismiss
 *   • Auto-prune expired toasts every 1s
 *   • Screen-reader accessible (role="status" aria-live="polite")
 */
import React, { useEffect, memo } from 'react'
import { useAlertStore } from '../alerts/alertStore'
import type { AlertSeverity } from '../alerts/alertEngine'

// ─────────────────────────────────────────────────────────────────────────────
// Severity tokens
// ─────────────────────────────────────────────────────────────────────────────

const SEV: Record<AlertSeverity, { border: string; bg: string; icon: string; label: string }> = {
    critical: { border: 'border-[#ef4444]/60', bg: 'bg-[#450a0a]/95', icon: '🔴', label: 'CRITICAL' },
    warning: { border: 'border-[#f59e0b]/60', bg: 'bg-[#422006]/95', icon: '🟡', label: 'WARN' },
    info: { border: 'border-[#3b82f6]/60', bg: 'bg-[#1e3a5f]/95', icon: '🔵', label: 'INFO' },
}

// ─────────────────────────────────────────────────────────────────────────────
// Single toast
// ─────────────────────────────────────────────────────────────────────────────

const Toast: React.FC<{ id: string; severity: AlertSeverity; title: string; body: string; onDismiss: (id: string) => void }> =
    memo(({ id, severity, title, body, onDismiss }) => {
        const s = SEV[severity]
        return (
            <div
                role="alert"
                aria-live="assertive"
                className={`flex items-start gap-2 px-3 py-2.5 rounded-lg border ${s.border} ${s.bg} shadow-[0_4px_24px_rgba(0,0,0,0.6)] backdrop-blur-sm cursor-pointer select-none w-[280px] transition-all duration-200`}
                onClick={() => onDismiss(id)}
                title="Click to dismiss"
            >
                <span className="text-[11px] mt-px shrink-0">{s.icon}</span>
                <div className="flex flex-col min-w-0">
                    <div className="flex items-center gap-1.5">
                        <span className="text-[8px] font-black tracking-widest text-white/40">{s.label}</span>
                        <span className="text-[10px] font-bold text-white/90 leading-tight truncate">{title}</span>
                    </div>
                    <p className="text-[9px] text-white/55 leading-snug mt-0.5 line-clamp-2">{body}</p>
                </div>
                <span className="text-white/20 text-[10px] font-bold ml-auto shrink-0 hover:text-white/50 transition-colors">✕</span>
            </div>
        )
    })

Toast.displayName = 'Toast'

// ─────────────────────────────────────────────────────────────────────────────
// Toast stack
// ─────────────────────────────────────────────────────────────────────────────

export const AlertToast: React.FC = memo(() => {
    const toasts = useAlertStore((s) => s.toasts)
    const dismiss = useAlertStore((s) => s.dismiss)
    const prune = useAlertStore((s) => s.prune)

    // Prune expired toasts every second
    useEffect(() => {
        const interval = setInterval(prune, 1_000)
        return () => clearInterval(interval)
    }, [prune])

    if (toasts.length === 0) return null

    return (
        <div
            className="fixed bottom-16 right-4 z-[9999] flex flex-col gap-2 items-end pointer-events-auto"
            role="status"
            aria-label="Alert notifications"
        >
            {[...toasts].reverse().map((t) => (
                <Toast
                    key={t.id}
                    id={t.id}
                    severity={t.severity}
                    title={t.title}
                    body={t.body}
                    onDismiss={dismiss}
                />
            ))}
        </div>
    )
})

AlertToast.displayName = 'AlertToast'

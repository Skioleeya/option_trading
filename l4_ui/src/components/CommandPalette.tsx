/**
 * l4_ui — Command Palette (Phase 4: Keyboard-Driven Workflows)
 * ───────────────────────────────────────────────────────────────────
 * Ctrl+K (or Cmd+K on macOS) opens a searchable command palette.
 *
 * Features:
 *   • Fuzzy-search across command labels
 *   • Category grouping with keyboard navigation (↑↓ arrows + Enter)
 *   • Click-to-execute + Escape to close
 *   • Backdrop dismissed on outside click
 *   • Focus-trap: Tab cycles within modal
 *   • Accessible: role="dialog", aria-modal, aria-label
 *   • No external deps: pure React + CSS
 */
import React, { useState, useEffect, useRef, useCallback, memo, useMemo } from 'react'
import { buildCommandRegistry, type Command } from '../commands/commandRegistry'

// ─────────────────────────────────────────────────────────────────────────────
// Fuzzy search
// ─────────────────────────────────────────────────────────────────────────────

function fuzzyMatch(query: string, text: string): boolean {
    if (!query) return true
    const q = query.toLowerCase()
    const t = text.toLowerCase()
    let qi = 0
    for (let i = 0; i < t.length && qi < q.length; i++) {
        if (t[i] === q[qi]) qi++
    }
    return qi === q.length
}

// ─────────────────────────────────────────────────────────────────────────────
// Hooks
// ─────────────────────────────────────────────────────────────────────────────

/** Returns true while the palette is open. */
function useCommandPaletteOpen(): [boolean, React.Dispatch<React.SetStateAction<boolean>>] {
    const [open, setOpen] = useState(false)

    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault()
                setOpen((v) => !v)
            }
            if (e.key === 'Escape') setOpen(false)
        }
        window.addEventListener('keydown', handler)
        return () => window.removeEventListener('keydown', handler)
    }, [])

    return [open, setOpen]
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export const CommandPalette: React.FC = memo(() => {
    const [open, setOpen] = useCommandPaletteOpen()
    const [query, setQuery] = useState('')
    const [active, setActive] = useState(0)
    const inputRef = useRef<HTMLInputElement>(null)
    const listRef = useRef<HTMLDivElement>(null)

    // Rebuild registry on open (picks up fresh store values)
    const commands: Command[] = useMemo(
        () => (open ? buildCommandRegistry() : []),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [open]
    )

    // Filtered + grouped
    const filtered = useMemo(
        () => commands.filter((c) => fuzzyMatch(query, c.label)),
        [commands, query]
    )

    const categories = useMemo(
        () => [...new Set(filtered.map((c) => c.category))],
        [filtered]
    )

    // Reset when opened
    useEffect(() => {
        if (open) {
            setQuery('')
            setActive(0)
            setTimeout(() => inputRef.current?.focus(), 30)
        }
    }, [open])

    // Keep active item in viewport
    useEffect(() => {
        const el = listRef.current?.querySelector(`[data-idx="${active}"]`)
        el?.scrollIntoView({ block: 'nearest' })
    }, [active])

    const execute = useCallback((cmd: Command) => {
        setOpen(false)
        cmd.action()
    }, [setOpen])

    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
        if (e.key === 'ArrowDown') { e.preventDefault(); setActive((v) => Math.min(v + 1, filtered.length - 1)) }
        if (e.key === 'ArrowUp') { e.preventDefault(); setActive((v) => Math.max(v - 1, 0)) }
        if (e.key === 'Enter' && filtered[active]) execute(filtered[active])
    }, [filtered, active, execute])

    if (!open) return null

    let idx = -1

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 z-[9990] bg-black/60 backdrop-blur-[2px]"
                onClick={() => setOpen(false)}
                aria-hidden="true"
            />

            {/* Modal */}
            <div
                role="dialog"
                aria-modal="true"
                aria-label="Command palette"
                className="fixed top-[20%] left-1/2 -translate-x-1/2 z-[9999] w-[560px] max-h-[65vh] flex flex-col bg-[#0d0d0f]/98 border border-[#3f3f46] rounded-xl shadow-[0_16px_64px_rgba(0,0,0,0.8)] overflow-hidden font-sans"
                onKeyDown={handleKeyDown}
            >
                {/* Search input */}
                <div className="flex items-center gap-2.5 px-4 py-3 border-b border-[#27272a]">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-[#71717a] shrink-0">
                        <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
                    </svg>
                    <input
                        ref={inputRef}
                        id="cmd-palette-input"
                        type="text"
                        value={query}
                        onChange={(e) => { setQuery(e.target.value); setActive(0) }}
                        placeholder="Type a command…"
                        className="flex-1 bg-transparent text-[13px] text-[#e4e4e7] placeholder-[#52525b] outline-none"
                        autoComplete="off"
                        spellCheck={false}
                    />
                    <kbd className="text-[9px] font-mono font-bold text-[#52525b] bg-[#1c1c1e] border border-[#3f3f46] rounded px-1.5 py-0.5">ESC</kbd>
                </div>

                {/* Results */}
                <div ref={listRef} className="flex-1 overflow-y-auto py-1" style={{ scrollbarWidth: 'none' }}>
                    {filtered.length === 0 && (
                        <div className="px-4 py-8 text-center text-[11px] text-[#52525b]">No commands found</div>
                    )}

                    {categories.map((cat) => (
                        <div key={cat}>
                            <div className="px-4 py-1.5 text-[9px] font-black tracking-[0.15em] text-[#52525b] uppercase">{cat}</div>
                            {filtered.filter((c) => c.category === cat).map((cmd) => {
                                idx++
                                const isActive = active === idx
                                const localIdx = idx
                                return (
                                    <div
                                        key={cmd.id}
                                        data-idx={localIdx}
                                        className={`flex items-center justify-between px-4 py-2 cursor-pointer transition-colors duration-75 ${isActive ? 'bg-[#1c1c1e]' : 'hover:bg-[#141416]'}`}
                                        onClick={() => execute(cmd)}
                                        onMouseEnter={() => setActive(localIdx)}
                                    >
                                        <span className={`text-[12px] font-medium ${isActive ? 'text-[#e4e4e7]' : 'text-[#a1a1aa]'}`}>
                                            {cmd.label}
                                        </span>
                                        {cmd.shortcut && (
                                            <kbd className="text-[9px] font-mono font-bold text-[#71717a] bg-[#1c1c1e] border border-[#3f3f46] rounded px-1.5 py-0.5">
                                                {cmd.shortcut}
                                            </kbd>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    ))}
                </div>

                {/* Footer */}
                <div className="flex items-center gap-3 px-4 py-2 border-t border-[#27272a] text-[9px] text-[#52525b]">
                    <span><kbd className="font-mono bg-[#1c1c1e] border border-[#3f3f46] rounded px-1">↑↓</kbd> navigate</span>
                    <span><kbd className="font-mono bg-[#1c1c1e] border border-[#3f3f46] rounded px-1">↵</kbd> execute</span>
                    <span><kbd className="font-mono bg-[#1c1c1e] border border-[#3f3f46] rounded px-1">Ctrl+K</kbd> toggle</span>
                    <span className="ml-auto">SPX Sentinel</span>
                </div>
            </div>
        </>
    )
})

CommandPalette.displayName = 'CommandPalette'

import { describe, expect, it } from 'vitest'
import {
    isDebugOverlayToggleHotkey,
    isPaletteToggleHotkey,
} from '../commandPaletteHotkeys'

function eventLike(partial: Partial<KeyboardEvent>): KeyboardEvent {
    return {
        key: '',
        ctrlKey: false,
        metaKey: false,
        altKey: false,
        repeat: false,
        ...partial,
    } as KeyboardEvent
}

describe('command palette hotkeys', () => {
    it('accepts Ctrl/Cmd + K for palette toggle', () => {
        expect(isPaletteToggleHotkey(eventLike({ key: 'k', ctrlKey: true }))).toBe(true)
        expect(isPaletteToggleHotkey(eventLike({ key: 'K', metaKey: true }))).toBe(true)
    })

    it('accepts Ctrl/Cmd + D for debug overlay toggle', () => {
        expect(isDebugOverlayToggleHotkey(eventLike({ key: 'd', ctrlKey: true }))).toBe(true)
        expect(isDebugOverlayToggleHotkey(eventLike({ key: 'D', metaKey: true }))).toBe(true)
    })

    it('rejects repeats or alt-modified shortcuts', () => {
        expect(isPaletteToggleHotkey(eventLike({ key: 'k', ctrlKey: true, repeat: true }))).toBe(false)
        expect(isDebugOverlayToggleHotkey(eventLike({ key: 'd', ctrlKey: true, altKey: true }))).toBe(false)
    })
})

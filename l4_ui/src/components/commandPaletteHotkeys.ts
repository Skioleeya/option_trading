type HotkeyEvent = Pick<
    KeyboardEvent,
    'key' | 'ctrlKey' | 'metaKey' | 'altKey' | 'repeat'
>

function normalizeKey(key: string): string {
    return key.toLowerCase()
}

function isMetaCombo(e: HotkeyEvent): boolean {
    return (e.ctrlKey || e.metaKey) && !e.altKey && !e.repeat
}

export function isPaletteToggleHotkey(e: HotkeyEvent): boolean {
    return isMetaCombo(e) && normalizeKey(e.key) === 'k'
}

export function isDebugOverlayToggleHotkey(e: HotkeyEvent): boolean {
    return isMetaCombo(e) && normalizeKey(e.key) === 'd'
}

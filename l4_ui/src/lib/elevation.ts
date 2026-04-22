export type ElevationTone = 'bull' | 'bear' | 'warn' | 'none'

export const ELEVATION_CLASS_BY_TONE: Record<ElevationTone, string> = {
    bull: 'ring-2 ring-inset ring-[rgba(239,68,68,0.7)] shadow-[0_0_12px_rgba(239,68,68,0.18)]',
    bear: 'ring-2 ring-inset ring-[rgba(16,185,129,0.7)] shadow-[0_0_12px_rgba(16,185,129,0.18)]',
    warn: 'ring-2 ring-inset ring-[rgba(245,158,11,0.75)] shadow-[0_0_12px_rgba(245,158,11,0.18)]',
    none: '',
}

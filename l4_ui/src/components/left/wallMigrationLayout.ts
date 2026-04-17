export function formatWallMigrationStrike(value: number | null | undefined): string {
    if (value == null || !Number.isFinite(value)) {
        return '—'
    }
    return Math.round(value).toString()
}

export function buildWallMigrationGridTemplate(): string {
    return 'var(--l4-wall-label-w) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, var(--l4-wall-state-w))'
}

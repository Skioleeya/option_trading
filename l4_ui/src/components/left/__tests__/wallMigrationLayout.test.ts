import {
    buildWallMigrationGridTemplate,
    formatWallMigrationStrike,
} from '../wallMigrationLayout'

describe('wallMigrationLayout', () => {
    it('formats wall strikes as integer labels for compact readability', () => {
        expect(formatWallMigrationStrike(711)).toBe('711')
        expect(formatWallMigrationStrike(711.0)).toBe('711')
        expect(formatWallMigrationStrike(710.49)).toBe('710')
        expect(formatWallMigrationStrike(null)).toBe('—')
    })

    it('keeps T1 T2 current on equal-width adaptive tracks', () => {
        expect(buildWallMigrationGridTemplate()).toBe(
            'var(--l4-wall-label-w) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, var(--l4-wall-state-w))'
        )
    })
})

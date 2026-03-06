import { describe, expect, it } from 'vitest'
import { fuzzyMatch } from '../commandPaletteSearch'

describe('fuzzyMatch', () => {
    it('returns true for empty query', () => {
        expect(fuzzyMatch('', 'Go to Spot')).toBe(true)
    })

    it('matches ordered characters case-insensitively', () => {
        expect(fuzzyMatch('gts', 'Go To Spot 5600')).toBe(true)
        expect(fuzzyMatch('iv', 'IV Regime Escalation')).toBe(true)
    })

    it('fails when order cannot be satisfied', () => {
        expect(fuzzyMatch('sg', 'Go To Spot')).toBe(false)
    })
})

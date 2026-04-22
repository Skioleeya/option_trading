import { fmtImpact } from '../utils'

describe('fmtImpact', () => {
    it('formats impact with compact numeric units and no currency prefix', () => {
        expect(fmtImpact(88_123.4)).toBe('88.1K')
        expect(fmtImpact(1_250_000)).toBe('1.3M')
        expect(fmtImpact(2_600_000_000)).toBe('2.6B')
    })

    it('preserves sign for negative values', () => {
        expect(fmtImpact(-4_560)).toBe('-4.6K')
    })

    it('formats sub-thousand values without fixed two-decimal fallback semantics', () => {
        expect(fmtImpact(88.1234)).toBe('88.1')
        expect(fmtImpact(9.876)).toBe('9.88')
        expect(fmtImpact(950)).toBe('950')
    })

    it('renders missing values as placeholder', () => {
        expect(fmtImpact(null)).toBe('—')
        expect(fmtImpact(undefined)).toBe('—')
    })
})

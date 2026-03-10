import { describe, expect, it } from 'vitest'
import { decodeColumnarRows, decodeHistoryRows } from '../historyColumnar'

describe('historyColumnar', () => {
    it('decodes schema=v2 columnar payload to row objects', () => {
        const payload = {
            schema: 'v2',
            encoding: 'columnar-json',
            columns: ['timestamp', 'straddle_pct', 'strike_changed'],
            rows: [
                ['2026-03-10T13:30:00-04:00', 0.01, false],
                ['2026-03-10T13:31:00-04:00', 0.015, true],
            ],
        }
        const decoded = decodeColumnarRows(payload)
        expect(decoded).toEqual([
            { timestamp: '2026-03-10T13:30:00-04:00', straddle_pct: 0.01, strike_changed: false },
            { timestamp: '2026-03-10T13:31:00-04:00', straddle_pct: 0.015, strike_changed: true },
        ])
    })

    it('returns v1 rows directly when history key exists', () => {
        const payload = {
            date: '20260310',
            history: [{ timestamp: 't1', straddle_pct: 0.01 }],
            count: 1,
        }
        const rows = decodeHistoryRows(payload, 'history')
        expect(rows).toEqual([{ timestamp: 't1', straddle_pct: 0.01 }])
    })

    it('returns null for malformed columnar payloads', () => {
        expect(decodeColumnarRows({ schema: 'v2', encoding: 'columnar-json', columns: ['a'], rows: [1] })).toBeNull()
        expect(decodeColumnarRows({ schema: 'v2', encoding: 'bad', columns: ['a'], rows: [[1]] })).toBeNull()
        expect(decodeHistoryRows({ count: 0 }, 'history')).toBeNull()
    })
})

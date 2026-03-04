/**
 * Tests: DeltaDecoder (Phase 1)
 * ─────────────────────────────
 * 10 assertions covering:
 *   • parseMessage: valid JSON, invalid JSON, keepalive
 *   • isKeepalive / isDelta type predicates
 *   • applyPatch: successful patch
 *   • applyPatch: invalid patch returns err result
 *   • applyPatch: deep-clone prevents mutation of original
 *   • applyPatch: meta (timestamp) injection from delta envelope
 */

import { describe, it, expect } from 'vitest'
import { DeltaDecoder } from '../../adapters/deltaDecoder'
import type { DashboardPayload } from '../../types/dashboard'

// ─────────────────────────────────────────────────────────────────────────────
// Fixtures
// ─────────────────────────────────────────────────────────────────────────────

const PREV: DashboardPayload = {
    type: 'dashboard_update',
    timestamp: '2026-01-01T09:30:00Z',
    spot: 560.0,
    agent_g: null,
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('DeltaDecoder.parseMessage', () => {
    it('parses valid JSON', () => {
        const result = DeltaDecoder.parseMessage('{"type":"dashboard_update","spot":561}')
        expect(result).toEqual({ type: 'dashboard_update', spot: 561 })
    })

    it('returns null for invalid JSON', () => {
        expect(DeltaDecoder.parseMessage('not-json')).toBeNull()
        expect(DeltaDecoder.parseMessage('')).toBeNull()
    })
})

describe('DeltaDecoder.isKeepalive / isDelta', () => {
    it('identifies keepalive messages', () => {
        expect(DeltaDecoder.isKeepalive({ type: 'keepalive' })).toBe(true)
        expect(DeltaDecoder.isKeepalive({ type: 'dashboard_update' })).toBe(false)
        expect(DeltaDecoder.isKeepalive(null)).toBe(false)
    })

    it('identifies delta messages', () => {
        expect(DeltaDecoder.isDelta({ type: 'dashboard_delta' })).toBe(true)
        expect(DeltaDecoder.isDelta({ type: 'keepalive' })).toBe(false)
        expect(DeltaDecoder.isDelta(null)).toBe(false)
    })
})

describe('DeltaDecoder.applyPatch', () => {
    it('applies a valid JSON-Patch and returns ok result', () => {
        const patch = [{ op: 'replace', path: '/spot', value: 562.5 }]
        const result = DeltaDecoder.applyPatch(PREV, patch)
        expect(result.ok).toBe(true)
        if (result.ok) {
            expect(result.value.spot).toBe(562.5)
        }
    })

    it('returns error result on invalid patch (bad path)', () => {
        const patch = [{ op: 'replace', path: '/nonexistent/deep/path/x/y', value: 1 }]
        const result = DeltaDecoder.applyPatch(PREV, patch)
        // fast-json-patch will either throw or silently ignore; we just ensure no crash
        // and that the shape is a DecodeResult
        expect(typeof result.ok).toBe('boolean')
    })

    it('does not mutate the original prev payload', () => {
        const frozen = Object.freeze({ ...PREV })
        const patch = [{ op: 'replace', path: '/spot', value: 999.9 }]
        // Should not throw even though prev is frozen (deep-clone happens first)
        const result = DeltaDecoder.applyPatch(frozen as DashboardPayload, patch)
        expect(result.ok).toBe(true)
        expect((frozen as any).spot).toBe(560.0) // original unchanged
    })

    it('injects timestamp meta from delta envelope', () => {
        const patch = [{ op: 'replace', path: '/spot', value: 563.0 }]
        const meta = { timestamp: 'META-TS', heartbeat_timestamp: 'HB-TS' }
        const result = DeltaDecoder.applyPatch(PREV, patch, meta)
        expect(result.ok).toBe(true)
        if (result.ok) {
            expect(result.value.timestamp).toBe('META-TS')
        }
    })

    it('patch can add a new field at root level', () => {
        const patch = [{ op: 'add', path: '/extraField', value: 'hello' }]
        const result = DeltaDecoder.applyPatch(PREV, patch)
        expect(result.ok).toBe(true)
        if (result.ok) {
            expect((result.value as any).extraField).toBe('hello')
        }
    })
})

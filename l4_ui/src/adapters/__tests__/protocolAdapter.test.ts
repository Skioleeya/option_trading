/**
 * Tests: ProtocolAdapter (Phase 1)
 * ──────────────────────────────────
 * 8 assertions covering:
 *   • Message routing: keepalive → skip (no store call)
 *   • Message routing: delta → DeltaDecoder.applyPatch → applyMergedPayload
 *   • Message routing: full update → applyFullUpdate
 *   • Message routing: invalid JSON → no crash
 *   • Reconnect: setConnectionStatus called on close
 *   • sendPing: no-op when disconnected
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ProtocolAdapter } from '../../adapters/protocolAdapter'
import type { DashboardPayload } from '../../types/dashboard'

// ─────────────────────────────────────────────────────────────────────────────
// WebSocket mock setup
// ─────────────────────────────────────────────────────────────────────────────

class MockWebSocket {
    static OPEN = 1
    static CLOSED = 3
    static instance: MockWebSocket | null = null
    readyState = 1 // OPEN
    binaryType = 'blob'
    onopen: (() => void) | null = null
    onmessage: ((e: { data: string }) => void) | null = null
    onclose: ((e: { code: number }) => void) | null = null
    onerror: (() => void) | null = null
    sentMessages: string[] = []

    constructor(public url: string) {
        MockWebSocket.instance = this
    }

    send(data: string) { this.sentMessages.push(data) }
    close(code: number = 1000) { this.onclose?.({ code }) }
    simulateOpen() { this.onopen?.() }
    simulateMessage(data: string) { this.onmessage?.({ data }) }
}

// Patch global WebSocket
vi.stubGlobal('WebSocket', MockWebSocket)

// ─────────────────────────────────────────────────────────────────────────────
// Fixtures
// ─────────────────────────────────────────────────────────────────────────────

const FULL_PAYLOAD: DashboardPayload = {
    type: 'dashboard_update',
    timestamp: '2026-01-01T09:30:00Z',
    spot: 560.0,
    agent_g: null,
}

function makeStore() {
    const setConnectionStatus = vi.fn()
    const applyFullUpdate = vi.fn()
    const applyMergedPayload = vi.fn()
    return { setConnectionStatus, applyFullUpdate, applyMergedPayload }
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('ProtocolAdapter message routing', () => {
    let store: ReturnType<typeof makeStore>
    let adapter: ProtocolAdapter

    beforeEach(() => {
        MockWebSocket.instance = null
        store = makeStore()
        adapter = new ProtocolAdapter({ url: 'ws://test', store })
        adapter.setPayloadGetter(() => FULL_PAYLOAD)
        adapter.connect()
        MockWebSocket.instance!.simulateOpen()
    })

    it('keepalive messages are ignored (no store call)', () => {
        MockWebSocket.instance!.simulateMessage(JSON.stringify({ type: 'keepalive' }))
        expect(store.applyFullUpdate).not.toHaveBeenCalled()
        expect(store.applyMergedPayload).not.toHaveBeenCalled()
    })

    it('full update messages call applyFullUpdate', () => {
        MockWebSocket.instance!.simulateMessage(JSON.stringify(FULL_PAYLOAD))
        expect(store.applyFullUpdate).toHaveBeenCalledOnce()
        expect(store.applyFullUpdate).toHaveBeenCalledWith(expect.objectContaining({ spot: 560.0 }))
    })

    it('delta messages call applyMergedPayload with patched result', () => {
        const deltaMsg = {
            type: 'dashboard_delta',
            patch: [{ op: 'replace', path: '/spot', value: 561.0 }],
            timestamp: 'T2',
        }
        MockWebSocket.instance!.simulateMessage(JSON.stringify(deltaMsg))
        expect(store.applyMergedPayload).toHaveBeenCalledOnce()
        const arg = store.applyMergedPayload.mock.calls[0][0] as DashboardPayload
        expect(arg.spot).toBe(561.0)
    })

    it('invalid JSON is silently ignored — no crash', () => {
        expect(() =>
            MockWebSocket.instance!.simulateMessage('not-json')
        ).not.toThrow()
        expect(store.applyFullUpdate).not.toHaveBeenCalled()
    })

    it('onclose triggers setConnectionStatus to disconnected', () => {
        // Clear the 'connecting' call that happened before open
        store.setConnectionStatus.mockClear()
        MockWebSocket.instance!.close()
        expect(store.setConnectionStatus).toHaveBeenCalledWith('disconnected')
    })

    it('delta without prior payload is silently skipped', () => {
        adapter.setPayloadGetter(() => null) // simulate no baseline
        const deltaMsg = {
            type: 'dashboard_delta',
            patch: [{ op: 'replace', path: '/spot', value: 999 }],
        }
        MockWebSocket.instance!.simulateMessage(JSON.stringify(deltaMsg))
        expect(store.applyMergedPayload).not.toHaveBeenCalled()
    })
})

describe('ProtocolAdapter sendPing', () => {
    it('sendPing sends "ping" on open socket', () => {
        MockWebSocket.instance = null
        const store = makeStore()
        const adapter = new ProtocolAdapter({ url: 'ws://test', store })
        adapter.connect()
        // Trigger open to set reconnect delay back to initial
        MockWebSocket.instance!.simulateOpen()
        adapter.sendPing()
        expect(MockWebSocket.instance!.sentMessages).toContain('ping')
    })

    it('sendPing is a no-op after disconnect (ws set to null)', () => {
        MockWebSocket.instance = null
        const store = makeStore()
        // Large delay so reconnect timer does not fire synchronously
        const adapter = new ProtocolAdapter({
            url: 'ws://test',
            store,
            initialReconnectDelayMs: 999_999,
            maxReconnectDelayMs: 999_999,
        })
        adapter.connect()
        MockWebSocket.instance!.simulateOpen()
        // disconnect() sets this.ws = null and closes socket
        // The close event triggers a scheduled reconnect (but won't fire synchronously)
        adapter.disconnect()
        // sendPing should silently do nothing — calling it must not throw
        expect(() => adapter.sendPing()).not.toThrow()
    })
})

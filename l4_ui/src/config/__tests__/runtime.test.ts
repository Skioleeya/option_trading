import { buildRuntimeConfig } from '../runtime'

describe('runtime config strict fast-fail', () => {
    it('builds browser-facing api/ws from current window host', () => {
        const cfg = buildRuntimeConfig(
            {
                VITE_BACKEND_ORIGIN: 'https://desk.local:9001',
                VITE_L4_ENABLE_CENTER_V2: 'true',
                VITE_L4_ENABLE_RIGHT_V2: 'false',
                VITE_L4_ENABLE_LEFT_V2: '1',
            },
            { location: { protocol: 'http:', host: 'localhost:5173' } }
        )

        expect(cfg.backendOrigin).toBe('https://desk.local:9001')
        expect(cfg.apiBase).toBe('')
        expect(cfg.wsUrl).toBe('ws://localhost:5173/ws/dashboard')
        expect(cfg.flags.centerV2).toBe(true)
        expect(cfg.flags.rightV2).toBe(false)
        expect(cfg.flags.leftV2).toBe(true)
    })

    it('allows missing VITE_BACKEND_ORIGIN in browser-facing mode and stays same-origin', () => {
        const cfg = buildRuntimeConfig(
            {
                VITE_L4_ENABLE_CENTER_V2: 'true',
            },
            { location: { protocol: 'http:', host: 'localhost:5173' } }
        )

        expect(cfg.backendOrigin).toBe('http://localhost:5173')
        expect(cfg.apiBase).toBe('')
        expect(cfg.wsUrl).toBe('ws://localhost:5173/ws/dashboard')
    })

    it('builds api/ws from VITE_BACKEND_ORIGIN when browser location is unavailable', () => {
        const cfg = buildRuntimeConfig({
            VITE_BACKEND_ORIGIN: 'https://desk.local:9001',
            VITE_L4_ENABLE_CENTER_V2: 'true',
            VITE_L4_ENABLE_RIGHT_V2: 'false',
            VITE_L4_ENABLE_LEFT_V2: '1',
        }, { location: null })

        expect(cfg.backendOrigin).toBe('https://desk.local:9001')
        expect(cfg.apiBase).toBe('https://desk.local:9001')
        expect(cfg.wsUrl).toBe('wss://desk.local:9001/ws/dashboard')
        expect(cfg.flags.centerV2).toBe(true)
        expect(cfg.flags.rightV2).toBe(false)
        expect(cfg.flags.leftV2).toBe(true)
    })

    it('throws when VITE_BACKEND_ORIGIN is missing without browser location', () => {
        expect(() => buildRuntimeConfig({}, { location: null })).toThrow(/VITE_BACKEND_ORIGIN is required/i)
    })

    it('throws when legacy endpoint vars are present', () => {
        expect(() =>
            buildRuntimeConfig({
                VITE_BACKEND_ORIGIN: 'http://127.0.0.1:8001',
                VITE_L4_API_BASE: 'http://127.0.0.1:8001',
            }, { location: null })
        ).toThrow(/legacy endpoint vars are forbidden/i)
    })

    it('throws when origin contains path/query/hash', () => {
        expect(() =>
            buildRuntimeConfig({
                VITE_BACKEND_ORIGIN: 'http://127.0.0.1:8001/api?v=1#x',
            }, { location: null })
        ).toThrow(/origin-only/i)
    })
})

import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

function resolveBackendOrigin(raw) {
    if (!raw || !raw.trim()) {
        throw new Error(
            '[vite] VITE_BACKEND_ORIGIN is required (example: http://127.0.0.1:8001).'
        )
    }
    let parsed
    try {
        parsed = new URL(raw.trim())
    } catch {
        throw new Error(`[vite] invalid VITE_BACKEND_ORIGIN: ${raw}`)
    }
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        throw new Error(`[vite] VITE_BACKEND_ORIGIN must use http/https, got ${parsed.protocol}`)
    }
    if (parsed.pathname !== '/' || parsed.search || parsed.hash) {
        throw new Error('[vite] VITE_BACKEND_ORIGIN must be origin-only (no path/query/hash).')
    }
    return parsed
}

export default defineConfig(({ mode, command }) => {
    const env = loadEnv(mode, process.cwd(), '')
    const isServe = command === 'serve'
    const backend = isServe
        ? resolveBackendOrigin(env.VITE_BACKEND_ORIGIN || process.env.VITE_BACKEND_ORIGIN)
        : null
    const wsTarget = backend
        ? `${backend.protocol === 'https:' ? 'wss:' : 'ws:'}//${backend.host}`
        : null

    return {
        plugins: [react()],
        ...(isServe ? {
            server: {
                port: 5173,
                proxy: {
                    '/ws': {
                        target: wsTarget,
                        ws: true,
                    },
                    '/api': {
                        target: backend.origin,
                        changeOrigin: true,
                    },
                },
            },
        } : {}),
    }
})

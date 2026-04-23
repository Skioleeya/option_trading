import { preview } from 'vite'
import baseConfigFactory from '../vite.config.mjs'

const rawOrigin = process.env.VITE_BACKEND_ORIGIN?.trim() || ''
if (!rawOrigin) {
    console.error(
        '[l4_ui preview] Missing VITE_BACKEND_ORIGIN. ' +
        'Use managed startup: `.venv\\\\Scripts\\\\python.exe manage.py start-all`.'
    )
    process.exit(1)
}

try {
    const parsed = new URL(rawOrigin)
    if (!['http:', 'https:'].includes(parsed.protocol)) {
        throw new Error(`VITE_BACKEND_ORIGIN must use http/https, got ${parsed.protocol}`)
    }
    if (parsed.pathname !== '/' || parsed.search || parsed.hash) {
        throw new Error('VITE_BACKEND_ORIGIN must be origin-only (no path/query/hash).')
    }
} catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    console.error(`[l4_ui preview] ${message}`)
    process.exit(1)
}

function parseArgs(argv) {
    const result = {
        host: undefined,
        port: undefined,
        open: undefined,
        strictPort: false,
    }

    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i]
        if (arg === '--host') {
            result.host = argv[i + 1]
            i += 1
            continue
        }
        if (arg === '--port') {
            result.port = Number(argv[i + 1])
            i += 1
            continue
        }
        if (arg === '--open') {
            const next = argv[i + 1]
            if (!next || next.startsWith('--')) {
                result.open = true
            } else {
                result.open = next
                i += 1
            }
            continue
        }
        if (arg === '--strictPort') {
            result.strictPort = true
        }
    }

    return result
}

const cli = parseArgs(process.argv.slice(2))
const config = baseConfigFactory({ mode: 'production', command: 'preview' })
config.configFile = false
config.preview = {
    ...(config.preview || {}),
    ...(cli.host ? { host: cli.host } : {}),
    ...(Number.isFinite(cli.port) ? { port: cli.port } : {}),
    ...(cli.open !== undefined ? { open: cli.open } : {}),
    ...(cli.strictPort ? { strictPort: true } : {}),
}

const server = await preview(config)

const closeServer = async (code = 0) => {
    try {
        await server.httpServer.close()
    } finally {
        process.exit(code)
    }
}

process.on('SIGINT', () => {
    void closeServer(0)
})
process.on('SIGTERM', () => {
    void closeServer(0)
})

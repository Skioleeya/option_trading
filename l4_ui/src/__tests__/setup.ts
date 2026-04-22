import '@testing-library/jest-dom'

type TestProcess = {
    env: Record<string, string | undefined>
}

const processRef = (globalThis as typeof globalThis & { process?: TestProcess }).process

if (processRef) {
    processRef.env.VITE_BACKEND_ORIGIN = processRef.env.VITE_BACKEND_ORIGIN || 'http://127.0.0.1:8001'
}

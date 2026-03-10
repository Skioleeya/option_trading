export interface ColumnarPayload {
    schema?: string
    encoding?: string
    columns?: unknown
    rows?: unknown
}

function isStringArray(value: unknown): value is string[] {
    return Array.isArray(value) && value.every((v) => typeof v === 'string')
}

function isRowArray(value: unknown): value is unknown[][] {
    return Array.isArray(value) && value.every((row) => Array.isArray(row))
}

export function decodeColumnarRows(payload: unknown): Record<string, unknown>[] | null {
    if (!payload || typeof payload !== 'object') return null
    const obj = payload as ColumnarPayload
    if (obj.schema !== 'v2') return null
    if (obj.encoding !== 'columnar-json') return null
    if (!isStringArray(obj.columns) || !isRowArray(obj.rows)) return null

    const columns = obj.columns
    return obj.rows.map((row) => {
        const out: Record<string, unknown> = {}
        for (let i = 0; i < columns.length; i += 1) {
            out[columns[i]] = row[i]
        }
        return out
    })
}

export function decodeHistoryRows(payload: unknown, rowKey: 'history' | 'records'): Record<string, unknown>[] | null {
    if (!payload || typeof payload !== 'object') return null
    const obj = payload as Record<string, unknown>
    const v1Rows = obj[rowKey]
    if (Array.isArray(v1Rows)) return v1Rows as Record<string, unknown>[]
    return decodeColumnarRows(payload)
}

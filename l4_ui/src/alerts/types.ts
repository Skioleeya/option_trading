export type AlertSeverity = 'info' | 'warning' | 'critical'

export interface L4Alert {
    id: string
    timestamp: number
    severity: AlertSeverity
    category: 'SIGNAL' | 'WALL' | 'GEX' | 'IV' | 'SPOT'
    title: string
    body: string
}

import { ConnectionMonitor } from './connectionMonitor'

// Wire it lightly into protocolAdapter.ts
// Just re-write protocolAdapter imports to include it.
// (In a real scenario, ProtocolAdapter calls ConnectionMonitor.onWsOpen() etc.)

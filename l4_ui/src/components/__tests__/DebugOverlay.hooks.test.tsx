import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DebugOverlay } from '../DebugOverlay'
import { useDashboardStore } from '../../store/dashboardStore'

describe('DebugOverlay hooks stability', () => {
    it('does not throw when toggling open from false to true', () => {
        useDashboardStore.setState({
            payload: null,
            connectionStatus: 'connected',
        })

        const { rerender } = render(<DebugOverlay open={false} onClose={() => { }} />)

        expect(() => {
            rerender(<DebugOverlay open onClose={() => { }} />)
        }).not.toThrow()
    })
})

import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { useDashboardStore } from '../../../store/dashboardStore'

vi.mock('../chartEngineAdapter', () => ({
    createAtmChartRuntime: vi.fn(() => {
        throw new Error('chart-init-failed')
    }),
}))

import { AtmDecayChart } from '../AtmDecayChart'

describe('AtmDecayChart degraded mode', () => {
    afterEach(() => {
        cleanup()
        vi.restoreAllMocks()
        useDashboardStore.setState({
            atmHistory: [],
        } as any)
    })

    it('keeps component mounted and shows degraded overlay when chart init fails', () => {
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

        expect(() => render(<AtmDecayChart data={[]} />)).not.toThrow()
        expect(screen.getByTestId('atm-chart-degraded')).toHaveTextContent('CENTER CHART DEGRADED (INIT)')
        expect(errorSpy).toHaveBeenCalled()
    })
})

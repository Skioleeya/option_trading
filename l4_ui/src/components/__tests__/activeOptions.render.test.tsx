import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { ActiveOption } from '../../types/dashboard'
import { ActiveOptions } from '../right/ActiveOptions'

function row(slot: number, partial: Partial<ActiveOption>): ActiveOption {
    return {
        symbol: 'SPY',
        option_type: 'CALL',
        strike: 560,
        implied_volatility: 0.2,
        volume: 1000,
        turnover: 100000,
        flow: 1000,
        impact_index: 50,
        slot_index: slot,
        ...partial,
    }
}

describe('ActiveOptions render contracts', () => {
    it('keeps fixed slot markers 1..5 across rerenders', () => {
        const { rerender, container } = render(
            <ActiveOptions
                options={[
                    row(5, { symbol: 'A', strike: 560 }),
                    row(1, { symbol: 'B', strike: 561 }),
                ]}
            />
        )

        let rows = Array.from(container.querySelectorAll('tbody tr'))
        expect(rows).toHaveLength(5)
        expect(rows.map((el) => el.getAttribute('data-slot'))).toEqual(['1', '2', '3', '4', '5'])

        rerender(
            <ActiveOptions
                options={[
                    row(2, { symbol: 'C', strike: 570 }),
                    row(4, { symbol: 'D', strike: 571 }),
                    row(1, { symbol: 'E', strike: 572 }),
                ]}
            />
        )

        rows = Array.from(container.querySelectorAll('tbody tr'))
        expect(rows).toHaveLength(5)
        expect(rows.map((el) => el.getAttribute('data-slot'))).toEqual(['1', '2', '3', '4', '5'])
    })

    it('renders negative FLOW with bearish green class even when backend color/direction conflict', () => {
        const { container } = render(
            <ActiveOptions
                options={[
                    row(1, {
                        flow: -320000,
                        flow_direction: 'BULLISH',
                        flow_color: 'text-accent-red',
                        flow_deg_formatted: '-$320K',
                        flow_volume_label: '12K',
                    }),
                ]}
            />
        )

        expect(screen.getByText('-$320K')).toBeInTheDocument()
        const flowCell = container.querySelector('tbody tr td:last-child')
        expect(flowCell).not.toBeNull()
        expect(flowCell!.className).toContain('text-accent-green')
        expect(flowCell!.className).not.toContain('text-accent-red')
    })

    it('renders neutral $0 instead of signed zero text', () => {
        render(
            <ActiveOptions
                options={[
                    row(1, {
                        flow: 0,
                        flow_direction: 'BEARISH',
                        flow_color: 'text-accent-green',
                        flow_deg_formatted: '-$0',
                    }),
                ]}
            />
        )

        expect(screen.getByText('$0')).toBeInTheDocument()
        expect(screen.queryByText('-$0')).not.toBeInTheDocument()
    })
})

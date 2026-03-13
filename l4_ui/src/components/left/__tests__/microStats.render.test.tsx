import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MicroStats } from '../MicroStats'

describe('MicroStats wall dyn semantics', () => {
    it('forces WALL DYN RETREAT to amber badge even when backend badge conflicts', () => {
        render(
            <MicroStats
                preferProp
                uiState={{
                    net_gex: { label: 'GEX +10M', badge: 'badge-red' },
                    wall_dyn: { label: 'RETREAT ↑', badge: 'badge-red' },
                    vanna: { label: 'NORMAL', badge: 'badge-neutral' },
                    momentum: { label: 'NEUTRAL', badge: 'badge-neutral' },
                }}
            />
        )

        const retreatBadge = screen.getByText('RETREAT ↑')
        expect(retreatBadge.className).toContain('badge-amber')
        expect(retreatBadge.className).not.toContain('badge-red')
    })
})

describe('MicroStats wall dyn hard-cut fallback', () => {
    it('forces unknown WALL DYN states to neutral and ignores backend badge color', () => {
        render(
            <MicroStats
                preferProp
                uiState={{
                    net_gex: { label: 'GEX +10M', badge: 'badge-red' },
                    wall_dyn: { label: 'CUSTOM SIGNAL', badge: 'badge-green' },
                    vanna: { label: 'NORMAL', badge: 'badge-neutral' },
                    momentum: { label: 'NEUTRAL', badge: 'badge-neutral' },
                }}
            />
        )

        const unknownBadge = screen.getByText('CUSTOM SIGNAL')
        expect(unknownBadge.className).toContain('badge-neutral')
        expect(unknownBadge.className).not.toContain('badge-green')
    })
})

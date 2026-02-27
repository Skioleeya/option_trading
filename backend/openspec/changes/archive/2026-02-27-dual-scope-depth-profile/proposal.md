# Proposal: Dual-Scope Dynamic Depth Profile

## Why
With the implementation of the Dynamic Strike Window (±15) and Research Scan (±70), the frontend `DepthProfile` component needs to evolve. Currently, it tries to render whatever is given to it, but the data is now split into two logical tiers. We need a UI that reflects this: a high-fidelity "Active Battlezone" that stays centered, and a low-fidelity "Macro Radar" that shows the wider liquidity landscape.

## What Changes
We will transform the `DepthProfile` into a **Dual-Scope UI**:
1.  **Micro-Battlefield (Center)**: Renders the high-frequency ±15 point data (GEX/Volume). It will automatically scroll to keep the `SPOT` price vertically centered.
2.  **Macro Minimap (Sidebar)**: A slender, vertical bar on the edge (similar to a code editor minimap) that visualizes the ±70 point `volume_map` gathered from the 15-minute research scans.
3.  **Data Mapping**: 
    - Main Bars = Net GEX or Open Interest (Structural defense)
    - Border/Glow = Real-time Volume velocity (Active flow)

## Capabilities
- **Capability: Auto-Centering Spot**: The UI will use `useEffect` and `scrollIntoView` to ensure the current SPY price is always in the dead center of the scrollable area.
- **Capability: Liquidity Minimap**: Render the wide-range volume peaks as a sparkline or heatmap strip to provide off-screen context.
- **Capability: Boundary Warnings**: Inject visual indicators (e.g., ⬆️/⬇️) at the top/bottom of the active list if the Minimap detects a massive wall just outside the current view.

## Impact
- **Reduced Cognitive Load**: Traders only see the most actionable ±15 strikes without losing the "big picture" context.
- **Dom Performance**: Rendering 30 rows + a simple SVG minimap is infinitely faster than rendering 140 complex rows.
- **Situational Awareness**: Solves the "tunnel vision" problem of dynamic windows by constantly showing where the massive liquidity pools exist outside the current range.

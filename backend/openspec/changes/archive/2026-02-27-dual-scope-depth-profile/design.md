# Design: Dual-Scope Depth Profile

## Architecture
```mermaid
graph TD
    WS[WebSocket Payload] -->|Active Chain (+/-15)| PROFILE[DepthProfile Component]
    WS -->|Volume Map (+/-70)| PROFILE
    
    PROFILE -->|Renders 30 Rows| ROWS[Micro-Battlefield Rows]
    PROFILE -->|Renders Map| MAP[SVG Minimap Sidebar]
    
    ROWS -->|Spot Row Ref| EFFECT[useEffect Scroll Handler]
    EFFECT -->|scrollIntoView| UI[Center UI on Spot]
```

## Data Integration
Currently, the backend `OptionChainBuilder` has `_volume_map` internally but does not broadcast it.
1.  **Backend Change**: Update `SnapshotBuilder` to extract `option_chain._volume_map` and append it to the WebSocket `ui_state` under a new key: `macro_volume_map`.
2.  **Frontend Interface**: `dashboard.ts` will be updated to include `macro_volume_map: Record<string, number>`.

## Visual Layout
- The `DepthProfile` flex container will be split:
  - `w-[4px]`: Left gutter (optional, currently unused)
  - `flex-1`: Main strike rows (Put Vol | Strike | Call Vol)
  - `w-[12px]`: New **Right Gutter** for the Minimap.

## Minimap Implementation
- Renders as a vertical `<svg>` or highly optimized `div` stack.
- Y-axis represents the full ±70 strike range.
- X-axis represents total absolute volume.
- A glowing rectangle overlays the Minimap to indicate the "Current Viewport" (the ±15 window).

## Auto-Scroll Implementation
- A React `useRef` array will track the DOM node for each strike row.
- When `ui_state.spot` crosses a whole strike boundary (e.g., moves from 684.2 to 684.6, triggering 685 as the new ATM), `useEffect` detects the prop change for `is_spot`.
- It executes `spotRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })`.

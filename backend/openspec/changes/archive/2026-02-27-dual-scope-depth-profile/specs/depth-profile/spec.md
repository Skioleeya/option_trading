# Specification: Dual-Scope Depth Profile
# MODIFIED depth-profile

## ADDED Requirements

### Requirement: Macro Volume Map Broadcast
The backend `SnapshotBuilder` SHALL include the wide-area volume distribution in the UI snapshot.

#### Scenario: Backend sends volume map
- **WHEN** the system generates a new snapshot tick
- **THEN** it retrieves the `_volume_map` from the `OptionChainBuilder`
- **THEN** it attaches it to the payload as `ui_state.macro_volume_map`

### Requirement: Auto-Centering Spot Row
The frontend `DepthProfile` component SHALL automatically maintain the Spot price row in the vertical center of its scrollable container.

#### Scenario: Spot price updates
- **WHEN** the component receives a new WebSocket tick
- **THEN** if the `is_spot` identifier has moved to a new row
- **THEN** the component executes `scrollIntoView(block: 'center')` on that specific DOM node
- **THEN** the scrolling occurs smoothly without jarring jumps.

### Requirement: Macro Minimap Rendering
The `DepthProfile` component SHALL render a vertical side-bar (Minimap) visualizing the `macro_volume_map`.

#### Scenario: Rendering the radar
- **WHEN** the `DepthProfile` receives the `macro_volume_map` prop
- **THEN** it draws a condensed visual representation (e.g., SVG bars) on the extreme right edge of the component.
- **THEN** the bars are scaled relative to the maximum volume found in the `macro_volume_map`.

### Requirement: Viewport Indicator
The Minimap SHALL clearly indicate which section corresponds to the currently active ±15 point window.

#### Scenario: Overlaying the viewport box
- **WHEN** rendering the Minimap
- **THEN** an overlay box or highlighted border highlights the subset of strikes that match the active `DepthProfile` rows.

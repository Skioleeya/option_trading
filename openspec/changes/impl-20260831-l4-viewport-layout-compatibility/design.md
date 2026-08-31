# Design: L4 Viewport Layout Compatibility

The existing `App` remains the orchestration boundary. A layout token builder
continues to derive CSS variables from `window.visualViewport` dimensions. The
first phase adds bounded fluid rail tokens and a center minimum so compact
windows absorb width changes continuously. A later phase may change grid areas
for genuinely narrow viewports, but will keep the existing `LeftPanel`, chart,
and `RightPanel` component boundaries intact.

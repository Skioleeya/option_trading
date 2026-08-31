# Proposal: L4 Viewport Layout Compatibility

CHANGE-ID: impl-20260831-l4-viewport-layout-compatibility

## Intent

Extend the L4 dashboard for compact browser viewports such as the display-2
`1072x874` window while preserving the existing panel boundaries and data
contracts.

## Constraints

- Layout decisions use viewport dimensions only; no physical-monitor identity.
- No whole-application transform scaling.
- Center chart, Wall Migration, Decision Engine, and Active Options retain their
  existing component and table contracts.
- Responsive behavior is implemented through neutral layout tokens and parent
  containers; panels do not import or coordinate with one another.

## Phases

1. Add fluid compact-workspace rail bounds and a center minimum constraint.
2. Add a narrow-viewport spatial reflow only when the center minimum cannot be
   satisfied.
3. Verify each phase against the live `localhost:5173` DOM and strict gates.

## Acceptance

- The 1072x874 viewport remains overflow-free.
- Core metrics remain present and readable in the compact workspace.
- Layout changes do not alter L4 protocol consumption or panel contracts.

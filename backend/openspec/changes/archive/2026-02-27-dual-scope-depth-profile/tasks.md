# Tasks: Dual-Scope Depth Profile (Phase 34)

## 1. Backend Data Exposure
- [x] 1.1 Update `OptionChainBuilder` to expose `_volume_map` via `get_volume_map()`
- [x] 1.2 Update `SnapshotBuilder.build_snapshot` to include `macro_volume_map` in the `ui_state` JSON payload

## 2. Frontend State Updates
- [x] 2.1 Update `OptionChainSnapshot` interface in `types.ts` (or relevant hook) to include `macro_volume_map: Record<string, number>`
- [x] 2.2 Wire the new data property down to the `DepthProfile` component

## 3. Micro-Battlefield (Auto-Scroll)
- [x] 3.1 Refactor `DepthProfile` to use `useRef` array or map to track row DOM nodes
- [x] 3.2 Implement `useEffect` triggered by `spot` changes to smoothly `scrollIntoView` the `is_spot` row
- [x] 3.3 Ensure the flex container layout correctly isolates scroll areas

## 4. Macro Minimap
- [x] 4.1 Update `DepthProfile` layout to include a Right Gutter (e.g., `w-[15px]`)
- [x] 4.2 Create a nested visually condensed representation (SVG or `div` bars) of `macro_volume_map`
- [x] 4.3 Add a distinct overlay/highlight indicating the current ±15 active zoom window

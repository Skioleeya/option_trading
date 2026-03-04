# Change: Real-time Breadth Alerts

## Why
Currently, the system monitors market breadth indicators but relies on the user to manually observe the charts and KPI cards for extreme values. In a fast-moving market, extreme breadth momentum (BM) or net breadth values often precede significant price movements or reversals. A proactive alert system will ensure the user never misses these critical market regimes.

## What Changes
- **Alert Logic**: Implement threshold-based triggers in the domain layer.
- **Audio Alerts**: Play a "beep" sound (using existing `assets/beep.wav`) when alerts are triggered in Live mode.
- **Visual Alert UI**: Add a "Recent Alerts" log or toast notification to the Dash dashboard.
- **Configuration**: Add configurable thresholds for BM, Net Breadth, and Change-over-time to `settings.py`.

## Impact
- Affected specs: `specs/alerts/spec.md` (NEW)
- Affected code:
  - `monitor/config/settings.py`: New alert thresholds.
  - `monitor/core/domain/breadth_analyzer.py`: Alert calculation logic.
  - `monitor/ui/callbacks.py`: UI integration for audio/visual alerts.
  - `monitor/ui/layout.py`: New UI elements for alert display.

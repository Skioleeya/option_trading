# Momentum Calibration Toolkit

Offline MOMENTUM threshold calibration toolkit (K-line first phase).

## Purpose

- Uses Longbridge `1m` history candlesticks to calibrate `roc_bull_threshold` and `roc_bear_threshold`.
- Keeps runtime parameters `bbo_confirmation_min`, `max_roc_reference`, and `confidence_floor` frozen to live config values.
- Reserves a research feature adapter interface but does not consume research history in this phase.

## Entrypoints

```powershell
python tools/momentum_calibration/workflows/stage1_train.py --symbol SPY.US --end-date 2026-03-10
python tools/momentum_calibration/workflows/stage2_oos.py --symbol SPY.US --train-run-id <stage1_run_id>
python tools/momentum_calibration/workflows/stage3_weekly_roll.py --symbol SPY.US --anchor-date 2026-03-10
```

## Outputs

`tools/momentum_calibration/outputs/<run_id>/`

- `candidate_momentum_signal.yaml`
- `metrics_train.json`
- `metrics_oos.json` (stage2 writes into the stage1 run directory)
- `weekly_roll.csv`

## Rate Budget

- Default budget: `max_rps=3`, `max_concurrency=2`
- Hard guarded by official limits: `<=10 req/s`, `<=5 concurrent`
- 429 / transport failures use exponential backoff retry.


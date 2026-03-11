#!/usr/bin/env python3
"""
Online Depth Profile reconciliation.

For each WS tick that carries depth_profile updates, compare:
1) Raw WS depth_profile rows
2) Rendered UI rows in DepthProfile component

Outputs tick-by-tick evidence as CSV + JSON.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import websockets
from playwright.async_api import Page, async_playwright


def _utc_now_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _to_finite_number(raw: Any) -> float | None:
    if not isinstance(raw, (int, float)):
        return None
    n = float(raw)
    if not math.isfinite(n):
        return None
    return n


def _to_bool(raw: Any) -> bool:
    return raw is True or raw == "true" or raw == 1 or raw == "1"


def _extract_depth_profile(msg: dict[str, Any]) -> list[dict[str, Any]] | None:
    mtype = msg.get("type")
    if mtype in ("dashboard_update", "dashboard_init"):
        rows = (((msg.get("agent_g") or {}).get("data") or {}).get("ui_state") or {}).get("depth_profile")
        return rows if isinstance(rows, list) else None
    if mtype == "dashboard_delta":
        changes = msg.get("changes")
        if not isinstance(changes, dict):
            return None
        ui_state_changes = changes.get("agent_g_ui_state")
        if not isinstance(ui_state_changes, dict):
            return None
        rows = ui_state_changes.get("depth_profile")
        return rows if isinstance(rows, list) else None
    return None


@dataclass
class DepthRow:
    strike: float
    put_width: float
    call_width: float
    is_spot: bool
    is_flip: bool


def _normalize_expected_rows(raw_rows: list[dict[str, Any]]) -> list[DepthRow]:
    normalized: list[dict[str, Any]] = []
    for row in raw_rows:
        src = row if isinstance(row, dict) else {}
        strike = _to_finite_number(src.get("strike"))
        if strike is None:
            continue
        put_pct = max(0.0, _to_finite_number(src.get("put_pct")) or 0.0)
        call_pct = max(0.0, _to_finite_number(src.get("call_pct")) or 0.0)
        normalized.append(
            {
                "strike": strike,
                "put_pct": put_pct,
                "call_pct": call_pct,
                "is_spot": _to_bool(src.get("is_spot")),
                "is_flip": _to_bool(src.get("is_flip")),
            }
        )

    if not normalized:
        return []

    max_put = max((r["put_pct"] for r in normalized), default=0.0)
    max_call = max((r["call_pct"] for r in normalized), default=0.0)
    out: list[DepthRow] = []
    for r in normalized:
        if r["put_pct"] > 0:
            put_width = max((r["put_pct"] / max_put) * 95.0, 1.0) if max_put > 0 else 1.0
        else:
            put_width = 0.0
        if r["call_pct"] > 0:
            call_width = max((r["call_pct"] / max_call) * 95.0, 1.0) if max_call > 0 else 1.0
        else:
            call_width = 0.0
        out.append(
            DepthRow(
                strike=r["strike"],
                put_width=put_width,
                call_width=call_width,
                is_spot=bool(r["is_spot"]),
                is_flip=bool(r["is_flip"]),
            )
        )
    return out


def _rows_hash(rows: list[DepthRow]) -> str:
    canonical = [
        {
            "strike": round(r.strike, 6),
            "put_width": round(r.put_width, 4),
            "call_width": round(r.call_width, 4),
            "is_spot": r.is_spot,
            "is_flip": r.is_flip,
        }
        for r in rows
    ]
    payload = json.dumps(canonical, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


async def _read_ui_rows(page: Page) -> list[DepthRow]:
    payload = await page.evaluate(
        """
() => {
  const rowNodes = Array.from(document.querySelectorAll('[data-strike]'));
  return rowNodes.map((row) => {
    const strikeRaw = row.getAttribute('data-strike');
    const strike = strikeRaw == null ? NaN : Number(strikeRaw);
    const putBar = row.querySelector('div.bg-gradient-to-l[style*="width"]');
    const callBar = row.querySelector('div.bg-gradient-to-r[style*="width"]');
    const putWidth = putBar ? Number.parseFloat(putBar.style.width || '0') : 0;
    const callWidth = callBar ? Number.parseFloat(callBar.style.width || '0') : 0;
    const text = (row.textContent || '').toUpperCase();
    return {
      strike,
      put_width: Number.isFinite(putWidth) ? putWidth : 0,
      call_width: Number.isFinite(callWidth) ? callWidth : 0,
      is_spot: text.includes('SPOT'),
      is_flip: text.includes('FLIP')
    };
  }).filter((r) => Number.isFinite(r.strike));
}
"""
    )
    if not isinstance(payload, list):
        return []
    out: list[DepthRow] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        strike = _to_finite_number(item.get("strike"))
        if strike is None:
            continue
        out.append(
            DepthRow(
                strike=strike,
                put_width=_to_finite_number(item.get("put_width")) or 0.0,
                call_width=_to_finite_number(item.get("call_width")) or 0.0,
                is_spot=bool(item.get("is_spot")),
                is_flip=bool(item.get("is_flip")),
            )
        )
    return out


def _rows_match(expected: list[DepthRow], observed: list[DepthRow], width_tol: float) -> bool:
    if len(expected) != len(observed):
        return False
    for e, o in zip(expected, observed):
        if abs(e.strike - o.strike) > 1e-6:
            return False
        if e.is_spot != o.is_spot or e.is_flip != o.is_flip:
            return False
        if abs(e.put_width - o.put_width) > width_tol:
            return False
        if abs(e.call_width - o.call_width) > width_tol:
            return False
    return True


@dataclass
class ReconcileRow:
    tick: int
    msg_type: str
    expected_rows: int
    observed_rows: int
    expected_hash: str
    observed_hash: str
    match: bool
    ui_converged_ms: int
    ws_timestamp: str
    expected_changed: bool
    observed_changed: bool
    captured_at_utc: str


async def _wait_for_ui_match(
    page: Page,
    expected_rows: list[DepthRow],
    timeout_ms: int,
    poll_ms: int,
    width_tol: float,
) -> tuple[list[DepthRow], bool, int]:
    start = datetime.now(UTC)
    last_observed: list[DepthRow] = []
    elapsed = 0
    while elapsed <= timeout_ms:
        observed = await _read_ui_rows(page)
        last_observed = observed
        if _rows_match(expected_rows, observed, width_tol=width_tol):
            return observed, True, elapsed
        await asyncio.sleep(poll_ms / 1000.0)
        elapsed = int((datetime.now(UTC) - start).total_seconds() * 1000)
    return last_observed, False, elapsed


async def run(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_now_compact()
    csv_path = out_dir / f"depth_profile_reconcile_{stamp}.csv"
    json_path = out_dir / f"depth_profile_reconcile_{stamp}.json"

    rows: list[ReconcileRow] = []
    skipped_msgs = 0
    total_msgs = 0
    last_expected_hash: str | None = None
    last_observed_hash: str | None = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not args.show_browser)
        page = await browser.new_page()
        await page.goto(args.ui_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(args.ui_boot_wait_ms)
        initial_ui_rows = await _read_ui_rows(page)
        if len(initial_ui_rows) == 0:
            await browser.close()
            raise RuntimeError("DepthProfile rows not found in UI. Ensure frontend is up and left panel rendered.")

        async with websockets.connect(args.ws_url, max_size=8_000_000) as ws:
            while len(rows) < args.samples:
                raw = await ws.recv()
                total_msgs += 1
                msg = json.loads(raw)
                msg_type = str(msg.get("type", "unknown"))
                depth_rows_raw = _extract_depth_profile(msg)
                if depth_rows_raw is None:
                    skipped_msgs += 1
                    continue
                expected_rows = _normalize_expected_rows(depth_rows_raw)
                observed_rows, ok, latency = await _wait_for_ui_match(
                    page=page,
                    expected_rows=expected_rows,
                    timeout_ms=args.match_timeout_ms,
                    poll_ms=args.poll_ms,
                    width_tol=args.width_tolerance,
                )
                expected_hash = _rows_hash(expected_rows)
                observed_hash = _rows_hash(observed_rows)
                expected_changed = expected_hash != (last_expected_hash or expected_hash)
                observed_changed = observed_hash != (last_observed_hash or observed_hash)
                rows.append(
                    ReconcileRow(
                        tick=len(rows) + 1,
                        msg_type=msg_type,
                        expected_rows=len(expected_rows),
                        observed_rows=len(observed_rows),
                        expected_hash=expected_hash,
                        observed_hash=observed_hash,
                        match=ok,
                        ui_converged_ms=latency,
                        ws_timestamp=str(msg.get("timestamp", "")),
                        expected_changed=expected_changed,
                        observed_changed=observed_changed,
                        captured_at_utc=datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                    )
                )
                last_expected_hash = expected_hash
                last_observed_hash = observed_hash

        await browser.close()

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "tick",
                "msg_type",
                "expected_rows",
                "observed_rows",
                "expected_hash",
                "observed_hash",
                "match",
                "ui_converged_ms",
                "ws_timestamp",
                "expected_changed",
                "observed_changed",
                "captured_at_utc",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    summary = {
        "samples_requested": args.samples,
        "samples_captured": len(rows),
        "matches": sum(1 for r in rows if r.match),
        "mismatches": sum(1 for r in rows if not r.match),
        "expected_changed_ticks": sum(1 for r in rows if r.expected_changed),
        "observed_changed_ticks": sum(1 for r in rows if r.observed_changed),
        "total_ws_messages_seen": total_msgs,
        "ws_messages_skipped_without_depth_profile": skipped_msgs,
        "ui_url": args.ui_url,
        "ws_url": args.ws_url,
        "csv_path": str(csv_path),
        "rows": [asdict(r) for r in rows],
    }
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[DepthReconcile] captured={summary['samples_captured']} match={summary['matches']} mismatch={summary['mismatches']}")
    print(f"[DepthReconcile] expected_changed={summary['expected_changed_ticks']} observed_changed={summary['observed_changed_ticks']}")
    print(f"[DepthReconcile] csv={csv_path}")
    print(f"[DepthReconcile] json={json_path}")
    return 0 if summary["samples_captured"] > 0 else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Online tick-by-tick DepthProfile WS vs UI reconciliation")
    parser.add_argument("--ui-url", default="http://127.0.0.1:5173", help="Frontend URL")
    parser.add_argument("--ws-url", default="ws://127.0.0.1:8001/ws/dashboard", help="Dashboard websocket URL")
    parser.add_argument("--samples", type=int, default=30, help="How many depth_profile ticks to reconcile")
    parser.add_argument("--match-timeout-ms", type=int, default=2500, help="Max wait for UI to reflect one WS tick")
    parser.add_argument("--poll-ms", type=int, default=80, help="UI poll interval")
    parser.add_argument("--ui-boot-wait-ms", type=int, default=2000, help="Initial wait after page load")
    parser.add_argument("--width-tolerance", type=float, default=0.35, help="Allowed UI bar width delta (percentage points)")
    parser.add_argument("--out-dir", default="tmp/reconcile", help="Output directory for CSV/JSON evidence")
    parser.add_argument("--show-browser", action="store_true", help="Run headed browser")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))


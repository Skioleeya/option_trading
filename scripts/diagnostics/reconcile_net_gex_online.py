#!/usr/bin/env python3
"""
Online net_gex reconciliation.

Compares:
1) Raw WS value: agent_g.data.net_gex (or delta changes.agent_g_data.net_gex)
2) Actual page text shown in GexStatusBar ("Net GEX" value)

Outputs strict tick-by-tick evidence as CSV + JSON.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
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


def _fmt_gex(value: float | None) -> str:
    # Keep formatting logic identical to l4_ui/src/lib/utils.ts::fmtGex
    if value is None:
        return "—"
    if abs(value) >= 1000:
        return f"{value / 1000:.2f}B"
    return f"{value:.2f}M"


def _to_finite_number(raw: Any) -> float | None:
    if not isinstance(raw, (int, float)):
        return None
    n = float(raw)
    if not math.isfinite(n):
        return None
    return n


def _extract_ws_net_gex(msg: dict[str, Any]) -> float | None:
    mtype = msg.get("type")
    if mtype in ("dashboard_update", "dashboard_init"):
        return _to_finite_number(((msg.get("agent_g") or {}).get("data") or {}).get("net_gex"))
    if mtype == "dashboard_delta":
        changes = msg.get("changes")
        if isinstance(changes, dict):
            agent_g_data = changes.get("agent_g_data")
            if isinstance(agent_g_data, dict):
                return _to_finite_number(agent_g_data.get("net_gex"))
            return _to_finite_number(changes.get("net_gex"))
    return None


@dataclass
class ReconcileRow:
    tick: int
    msg_type: str
    raw_net_gex: float
    expected_ui_text: str
    observed_ui_text: str
    observed_ui_class: str
    match: bool
    ui_converged_ms: int
    ws_timestamp: str
    captured_at_utc: str


async def _read_ui_net_gex(page: Page) -> tuple[str | None, str]:
    payload = await page.evaluate(
        """
() => {
  const spans = Array.from(document.querySelectorAll('span'));
  const label = spans.find((s) => (s.textContent || '').trim() === 'Net GEX');
  if (!label) return { text: null, className: '' };
  const box = label.parentElement;
  if (!box) return { text: null, className: '' };
  const value = box.querySelector('span.font-mono');
  if (!value) return { text: null, className: '' };
  return {
    text: (value.textContent || '').trim(),
    className: value.className || '',
  };
}
"""
    )
    if not isinstance(payload, dict):
        return None, ""
    text = payload.get("text")
    class_name = payload.get("className")
    return (text if isinstance(text, str) and text else None), (class_name if isinstance(class_name, str) else "")


async def _wait_for_ui_match(
    page: Page,
    expected_text: str,
    timeout_ms: int,
    poll_ms: int,
) -> tuple[str, str, bool, int]:
    start = datetime.now(UTC)
    last_text = ""
    last_class = ""
    elapsed = 0
    while elapsed <= timeout_ms:
        text, class_name = await _read_ui_net_gex(page)
        if text is not None:
            last_text = text
            last_class = class_name
            if text == expected_text:
                return last_text, last_class, True, elapsed
        await asyncio.sleep(poll_ms / 1000.0)
        elapsed = int((datetime.now(UTC) - start).total_seconds() * 1000)
    return last_text, last_class, False, elapsed


async def run(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_now_compact()
    csv_path = out_dir / f"net_gex_reconcile_{stamp}.csv"
    json_path = out_dir / f"net_gex_reconcile_{stamp}.json"

    rows: list[ReconcileRow] = []
    skipped_msgs = 0
    total_msgs = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not args.show_browser)
        page = await browser.new_page()
        await page.goto(args.ui_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(args.ui_boot_wait_ms)
        ui_boot_text, _ = await _read_ui_net_gex(page)
        if ui_boot_text is None:
            await browser.close()
            raise RuntimeError("UI 'Net GEX' element not found. Ensure frontend is up and chart layout rendered.")

        async with websockets.connect(args.ws_url, max_size=8_000_000) as ws:
            while len(rows) < args.samples:
                raw = await ws.recv()
                total_msgs += 1
                msg = json.loads(raw)
                msg_type = str(msg.get("type", "unknown"))
                net_gex = _extract_ws_net_gex(msg)
                if net_gex is None:
                    skipped_msgs += 1
                    continue

                expected = _fmt_gex(net_gex)
                ui_text, ui_class, ok, latency = await _wait_for_ui_match(
                    page=page,
                    expected_text=expected,
                    timeout_ms=args.match_timeout_ms,
                    poll_ms=args.poll_ms,
                )
                rows.append(
                    ReconcileRow(
                        tick=len(rows) + 1,
                        msg_type=msg_type,
                        raw_net_gex=net_gex,
                        expected_ui_text=expected,
                        observed_ui_text=ui_text,
                        observed_ui_class=ui_class,
                        match=ok,
                        ui_converged_ms=latency,
                        ws_timestamp=str(msg.get("timestamp", "")),
                        captured_at_utc=datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                    )
                )

        await browser.close()

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "tick",
                "msg_type",
                "raw_net_gex",
                "expected_ui_text",
                "observed_ui_text",
                "observed_ui_class",
                "match",
                "ui_converged_ms",
                "ws_timestamp",
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
        "total_ws_messages_seen": total_msgs,
        "ws_messages_skipped_without_net_gex": skipped_msgs,
        "ui_url": args.ui_url,
        "ws_url": args.ws_url,
        "csv_path": str(csv_path),
        "rows": [asdict(r) for r in rows],
    }
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[Reconcile] captured={summary['samples_captured']} match={summary['matches']} mismatch={summary['mismatches']}")
    print(f"[Reconcile] csv={csv_path}")
    print(f"[Reconcile] json={json_path}")
    return 0 if summary["samples_captured"] > 0 else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Online 1:1 net_gex WS vs UI reconciliation")
    parser.add_argument("--ui-url", default="http://127.0.0.1:5173", help="Frontend URL")
    parser.add_argument("--ws-url", default="ws://127.0.0.1:8001/ws/dashboard", help="Dashboard websocket URL")
    parser.add_argument("--samples", type=int, default=40, help="How many net_gex ticks to reconcile")
    parser.add_argument("--match-timeout-ms", type=int, default=2500, help="Max wait for UI to reflect one WS tick")
    parser.add_argument("--poll-ms", type=int, default=80, help="UI poll interval")
    parser.add_argument("--ui-boot-wait-ms", type=int, default=2000, help="Initial wait after page load")
    parser.add_argument("--out-dir", default="tmp/reconcile", help="Output directory for CSV/JSON evidence")
    parser.add_argument("--show-browser", action="store_true", help="Run headed browser")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))

"""IV/OI Pipeline Integrity Test — L0 through L4.

验证 IV 和 OI 在 L0→L4 每一层都正确流动。
通过连接运行中的后端 WebSocket 读取完整 payload，逐层检查关键字段。

运行方式:
    cd e:\\US.market\\Option_v3
    python scripts/test_iv_oi_pipeline.py
"""

import asyncio
import json
import sys
from colorama import Fore, Style, init

init(autoreset=True)

WS_URL = "ws://localhost:8001/ws/dashboard"
TIMEOUT_SEC = 20
MAX_MSGS = 60

# ─── Helpers ──────────────────────────────────────────────────────────────────

def ok(label: str, val: str = "") -> None:
    print(f"  {Fore.GREEN}✅ {label:<38}{Style.RESET_ALL} {val}")

def fail(label: str, val: str = "") -> None:
    print(f"  {Fore.RED}❌ {label:<38}{Style.RESET_ALL} {val}")

def warn(label: str, val: str = "") -> None:
    print(f"  {Fore.YELLOW}⚠️  {label:<37}{Style.RESET_ALL} {val}")

def section(title: str) -> None:
    print(f"\n{Fore.CYAN}{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}{Style.RESET_ALL}")

# ─── Main test ────────────────────────────────────────────────────────────────

async def run_test() -> None:
    import websockets

    print(f"\n{Fore.CYAN}{'='*55}")
    print(f"  IV/OI PIPELINE INTEGRITY  L0 → L4")
    print(f"{'='*55}{Style.RESET_ALL}")
    print(f"\n[*] Connecting to {WS_URL} ...")

    try:
        async with websockets.connect(WS_URL, open_timeout=5) as ws:
            print(f"{Fore.GREEN}[+] Connected{Style.RESET_ALL}")

            # ── Accumulate a full payload ─────────────────────────────────────
            state: dict = {}
            for i in range(MAX_MSGS):
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_SEC)
                except asyncio.TimeoutError:
                    print(f"{Fore.YELLOW}[!] Timeout after {TIMEOUT_SEC}s — using last partial state{Style.RESET_ALL}")
                    break

                msg = json.loads(raw)
                mtype = msg.get("type", "")

                if mtype in ("dashboard_init", "dashboard_update"):
                    state = msg
                    # We have a full payload — check if data is warm enough
                    ad = state.get("agent_g", {}).get("data", {})
                    if ad.get("spy_atm_iv", 0) > 0 and ad.get("net_gex", 0) != 0:
                        print(f"[*] Warm payload received after {i+1} messages")
                        break
                elif mtype == "dashboard_delta" and state:
                    changes = msg.get("changes", {})
                    ad = state.setdefault("agent_g", {}).setdefault("data", {})
                    ui = ad.setdefault("ui_state", {})
                    if "agent_g_ui_state" in changes:
                        ui.update(changes["agent_g_ui_state"])
                    for k, v in changes.items():
                        if k not in ("agent_g_ui_state",):
                            state[k] = v
                    if ad.get("spy_atm_iv", 0) > 0 and ad.get("net_gex", 0) != 0:
                        print(f"[*] Warm delta applied after {i+1} messages")
                        break

            if not state:
                print(f"{Fore.RED}[!] No payload received — is the backend alive?{Style.RESET_ALL}")
                return

    except ConnectionRefusedError:
        print(f"{Fore.RED}[!] Connection refused — is uvicorn running on port 8001?{Style.RESET_ALL}")
        return
    except Exception as e:
        print(f"{Fore.RED}[!] WS error: {e}{Style.RESET_ALL}")
        return

    # ── Parse payload ─────────────────────────────────────────────────────────
    ad   = state.get("agent_g", {}).get("data", {})
    ui   = ad.get("ui_state", {})
    spot = state.get("spot", 0)

    # ─────────────────────────────────────────────────────────────────────────
    section("L0 — Ingestion / IV Cache (REST)")
    # ─────────────────────────────────────────────────────────────────────────
    # spy_atm_iv arriving at L4 proves iv_cache was populated in L0
    atm_iv_l4 = ad.get("spy_atm_iv", 0)
    if atm_iv_l4 and atm_iv_l4 > 0:
        ok("IV reached L4 (spy_atm_iv)", f"{atm_iv_l4*100:.2f}%" if atm_iv_l4 < 2 else f"{atm_iv_l4:.2f}%")
    else:
        fail("IV reached L4 (spy_atm_iv)", f"value={atm_iv_l4!r}  ← REST iv_cache empty?")

    if spot and float(spot) > 0:
        ok("Live spot propagated", f"SPY {spot:.2f}")
    else:
        fail("Live spot missing", f"got={spot!r}")

    drift_ms = state.get("drift_ms", None)
    if drift_ms is not None:
        label = "L0 snapshot drift"
        if drift_ms < 500:
            ok(label, f"{drift_ms:.0f}ms")
        elif drift_ms < 1500:
            warn(label, f"{drift_ms:.0f}ms  (slightly elevated)")
        else:
            fail(label, f"{drift_ms:.0f}ms  (stale snapshot → data lag)")

    # ─────────────────────────────────────────────────────────────────────────
    section("L1 — Compute / Greeks (BSM × IV × OI)")
    # ─────────────────────────────────────────────────────────────────────────
    net_gex   = ad.get("net_gex", 0)
    net_vanna = ui.get("micro_stats", {}).get("vanna", {}).get("label", "—")
    atm_label = ui.get("micro_stats", {}).get("net_gex", {}).get("label", "—")

    if net_gex and net_gex != 0:
        ok("GEX computed (OI × gamma)", f"{net_gex:+,.0f}B" if abs(net_gex) > 1e6 else f"{net_gex:+.2f}")
    else:
        fail("GEX computed (net_gex)", f"={net_gex}  ← OI missing or IV missing?")

    if net_vanna and net_vanna != "—":
        ok("Vanna flow computed (IV → vanna)", net_vanna)
    else:
        fail("Vanna flow missing", "check iv_cache populated in greeks_engine")

    if atm_label and atm_label != "—":
        ok("ATM GEX label present", atm_label)
    else:
        warn("ATM GEX label", "still initializing or '—'")

    # GEX walls
    gamma_walls = ad.get("gamma_walls", {})
    call_wall   = gamma_walls.get("call_wall")
    put_wall    = gamma_walls.get("put_wall")
    if call_wall:
        ok("Call wall from GEX (OI-driven)", f"${call_wall:.0f}")
    else:
        fail("Call wall missing", "OI/GEX not forming GEX walls")
    if put_wall:
        ok("Put wall from GEX (OI-driven)", f"${put_wall:.0f}")
    else:
        fail("Put wall missing", "OI/GEX not forming GEX walls")

    # ─────────────────────────────────────────────────────────────────────────
    section("L3 — Assembly / Presenters")
    # ─────────────────────────────────────────────────────────────────────────
    depth = ui.get("depth_profile", [])
    if depth:
        # Check if OI is influencing the depth profile (non-zero bar heights)
        nonzero = [r for r in depth if r.get("call_pct", 0) != 0 or r.get("put_pct", 0) != 0]
        ok("Depth Profile rows", f"{len(depth)} rows, {len(nonzero)} with nonzero OI")
        if nonzero:
            s = nonzero[0]
            ok("Sample depth row", f"strike={s.get('strike')} call={s.get('call_pct',0):.1f}% put={s.get('put_pct',0):.1f}%")
        else:
            fail("Depth profile all zero", "OI not populating bars — GEX/OI not flowing to L3")
    else:
        fail("Depth Profile empty", "OI → Presenter not connected")

    walls = ui.get("wall_migration", [])
    # WallMigrationRow.label = type_label = "C" | "P"  (set in WallMigrationPresenterV2._row_from_dict)
    call_row = next((w for w in walls if w.get("label") == "C"), None)
    put_row  = next((w for w in walls if w.get("label") == "P"), None)
    if call_row:
        ok("Wall Migration CALL row (C)", f"strike={call_row.get('strike')}  state={call_row.get('state')}")
    else:
        fail("Wall Migration CALL missing", f"{len(walls)} rows, labels={[w.get('label') for w in walls]}")
    if put_row:
        ok("Wall Migration PUT row (P)", f"strike={put_row.get('strike')}  state={put_row.get('state')}")
    else:
        fail("Wall Migration PUT missing", f"{len(walls)} rows total")

    # ─────────────────────────────────────────────────────────────────────────
    section("L4 — Broadcast Payload Fields")
    # ─────────────────────────────────────────────────────────────────────────
    gfl = ad.get("gamma_flip_level", 0)
    if gfl and gfl != 0:
        ok("Gamma Flip Level", f"${gfl:.0f}")
    else:
        warn("Gamma Flip Level = 0", "may be valid (no flip in range)")

    direction  = ad.get("direction", "—")
    confidence = ad.get("confidence", 0)
    if direction and direction != "—":
        ok("L2 Signal direction", f"{direction}  ({confidence*100:.0f}% confidence)")
    else:
        fail("L2 Signal missing", "check reactor / decision engine")

    ts = state.get("data_timestamp", "—")
    ok("Payload timestamp", ts)

    # ─────────────────────────────────────────────────────────────────────────
    section("SUMMARY")
    # ─────────────────────────────────────────────────────────────────────────
    iv_ok  = atm_iv_l4 and atm_iv_l4 > 0
    oi_ok  = net_gex and net_gex != 0
    l3_ok  = len(depth) > 0 and len(nonzero if depth else []) > 0
    wall_ok = call_row is not None and put_row is not None

    items = [
        ("IV 通路 (L0 REST → L1 BSM → L4)", iv_ok),
        ("OI 通路 (L0 REST → L1 GEX → L4)", oi_ok),
        ("L3 Depth Profile 由 OI 驱动",      l3_ok),
        ("L3 Wall Migration 由 GEX 驱动",     wall_ok),
    ]
    passed = sum(1 for _, v in items if v)
    for label, v in items:
        (ok if v else fail)(label)

    color = Fore.GREEN if passed == len(items) else (Fore.YELLOW if passed >= 2 else Fore.RED)
    print(f"\n{color}  {passed}/{len(items)} 通路验证通过{Style.RESET_ALL}\n")


if __name__ == "__main__":
    try:
        import websockets  # noqa: F401
    except ImportError:
        print("请先安装: pip install websockets colorama")
        sys.exit(1)
    asyncio.run(run_test())

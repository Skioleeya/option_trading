import asyncio
import json

import pytest
import websockets

WS_URL = "ws://localhost:8001/ws/dashboard"
MAX_MESSAGES = 50
RECV_TIMEOUT_SEC = 15.0


def _merge_delta(current_state: dict, delta: dict) -> None:
    changes = delta.get("changes", {})
    if not isinstance(changes, dict):
        return

    if "agent_g_ui_state" in changes:
        ui_state = current_state.setdefault("agent_g", {}).setdefault("data", {}).setdefault("ui_state", {})
        ui_state.update(changes["agent_g_ui_state"])

    if "signal" in changes:
        signal_data = current_state.setdefault("agent_g", {}).setdefault("data", {})
        signal_data.update(changes["signal"])

    for key, value in changes.items():
        if key not in ("agent_g_ui_state", "signal"):
            current_state[key] = value


def _is_enriched_state(state: dict) -> bool:
    agent_data = state.get("agent_g", {}).get("data", {})
    ui_state = agent_data.get("ui_state", {})
    walls = ui_state.get("wall_migration", [])
    return isinstance(walls, list) and len(walls) > 0 and any(isinstance(w, dict) and "label" in w for w in walls)


@pytest.mark.asyncio
async def test_l0_l4_pipeline() -> None:
    current_state: dict | None = None
    last_raw_message = ""

    async with websockets.connect(WS_URL, open_timeout=5, ping_timeout=10) as websocket:
        for _ in range(MAX_MESSAGES):
            last_raw_message = await asyncio.wait_for(websocket.recv(), timeout=RECV_TIMEOUT_SEC)
            message = json.loads(last_raw_message)
            message_type = message.get("type")

            if message_type in ("dashboard_init", "dashboard_update") and "agent_g" in message:
                current_state = message
            elif message_type == "dashboard_delta" and current_state is not None:
                _merge_delta(current_state, message)
            elif message_type == "keepalive":
                continue
            else:
                continue

            if current_state is not None and _is_enriched_state(current_state):
                break

    assert current_state is not None, (
        f"Failed to assemble enriched dashboard payload within {MAX_MESSAGES} messages. "
        f"Last message={last_raw_message[:240]}"
    )

    spot = current_state.get("spot")
    assert spot is not None and float(spot) > 0, f"Invalid spot propagated from L0: {spot!r}"

    rust_active = current_state.get("rust_active")
    assert rust_active is True, f"rust_active must be true in hard-fail mode, got {rust_active!r}"

    shm_stats = current_state.get("shm_stats")
    assert isinstance(shm_stats, dict), f"Missing shm_stats in payload: {shm_stats!r}"
    assert shm_stats.get("status") == "OK", f"Expected shm_stats.status=OK, got {shm_stats.get('status')!r}"

    data_timestamp = current_state.get("data_timestamp") or current_state.get("timestamp")
    assert data_timestamp, "Missing data timestamp in assembled payload."

    agent_data = current_state.get("agent_g", {}).get("data", {})
    assert isinstance(agent_data, dict) and agent_data, "Missing agent_g.data payload."
    ui_state = agent_data.get("ui_state", {})
    assert isinstance(ui_state, dict), "Missing ui_state in agent payload."

    micro_stats = ui_state.get("micro_stats", {})
    net_gex_label = (micro_stats.get("net_gex") or {}).get("label")
    assert net_gex_label not in (None, "", "—"), f"Missing net_gex label in micro_stats: {micro_stats!r}"

    direction = agent_data.get("direction")
    confidence = agent_data.get("confidence")
    assert direction, f"Missing L2 direction in payload: {agent_data!r}"
    assert confidence is not None, f"Missing L2 confidence in payload: {agent_data!r}"

    walls = ui_state.get("wall_migration", [])
    assert isinstance(walls, list) and len(walls) > 0, "Missing L3 wall_migration rows."
    labels = {str(row.get("label")) for row in walls if isinstance(row, dict)}
    assert "C" in labels and "P" in labels, f"Expected CALL/PUT wall rows, got labels={sorted(labels)}"

    depth = ui_state.get("depth_profile", [])
    assert isinstance(depth, list) and len(depth) > 0, "Missing L3 depth_profile rows."

    governor = current_state.get("governor_telemetry")
    assert isinstance(governor, dict) and governor, "Missing governor_telemetry in top-level payload."


if __name__ == "__main__":
    asyncio.run(test_l0_l4_pipeline())

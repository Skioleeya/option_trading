from pathlib import Path

from scripts.diag.check_active_options_freeze_rootcause import build_diagnosis


def test_detects_retain_root_cause_with_runtime_activity() -> None:
    logs = [
        "\n".join(
            [
                "[ActiveOptionsRuntimeService] No options above min_volume threshold — retaining last valid payload (market closed or cold-start).",
                "INFO:     connection open",
                "[Debug] L0 Fetch: rust_active=True shm_stats=True",
                "[ActiveOptionsRuntimeService] No options above min_volume threshold — retaining last valid payload (market closed or cold-start).",
                "[Debug] L0 Fetch: rust_active=True shm_stats=True",
                "[ActiveOptionsRuntimeService] No options above min_volume threshold — retaining last valid payload (market closed or cold-start).",
                "[Debug] L0 Fetch: rust_active=True shm_stats=True",
            ]
        )
    ]
    runtime_text = "logger.warning('retaining last valid payload')"
    out = build_diagnosis(logs, runtime_text, retain_threshold=3, l0_fetch_threshold=3)
    assert out.verdict == "YES"
    assert out.likely_root_cause is True
    assert out.confidence == "HIGH"


def test_detects_placeholder_mode_as_not_this_root_cause() -> None:
    logs = [
        "\n".join(
            [
                "[ActiveOptionsRuntimeService] No options above min_volume threshold — emitting neutral placeholders to keep fixed row contract.",
                "[ActiveOptionsRuntimeService] No options above min_volume threshold — emitting neutral placeholders to keep fixed row contract.",
                "[ActiveOptionsRuntimeService] No options above min_volume threshold — emitting neutral placeholders to keep fixed row contract.",
            ]
        )
    ]
    runtime_text = "logger.warning('emitting neutral placeholders')"
    out = build_diagnosis(logs, runtime_text, retain_threshold=3, l0_fetch_threshold=1)
    assert out.verdict == "NO"
    assert out.likely_root_cause is False
    assert out.confidence == "HIGH"


def test_returns_inconclusive_when_evidence_missing() -> None:
    logs = ["INFO no useful lines here"]
    runtime_text = "pass"
    out = build_diagnosis(logs, runtime_text, retain_threshold=3, l0_fetch_threshold=3)
    assert out.verdict == "INCONCLUSIVE"
    assert out.likely_root_cause is False
    assert out.confidence == "LOW"

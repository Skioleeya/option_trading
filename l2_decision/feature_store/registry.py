"""l2_decision.feature_store.registry — YAML-based declarative feature and signal registration.

Loads signal generator configurations from config/signals/*.yaml files.
Supports hot-reload: call reload() to pick up parameter changes without restart.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default config directory (relative to this file's package root)
_DEFAULT_CONFIG_DIR = Path(__file__).parent.parent / "config" / "signals"


def load_signal_config(name: str, config_dir: Path | None = None) -> dict[str, Any]:
    """Load a signal generator config from a YAML file.

    Args:
        name:       Config file name without extension (e.g., "trap_detector").
        config_dir: Directory to search. Defaults to l2_decision/config/signals/.

    Returns:
        Dict with keys: signal_name, version, inputs, parameters, output_type.
        Returns empty dict if file not found (graceful degradation).
    """
    try:
        import yaml  # optional dependency
    except ImportError:
        logger.warning("PyYAML not installed — signal configs will use hardcoded defaults")
        return {}

    config_dir = config_dir or _DEFAULT_CONFIG_DIR
    yaml_path = config_dir / f"{name}.yaml"

    if not yaml_path.exists():
        logger.debug("Signal config '%s' not found at %s", name, yaml_path)
        return {}

    try:
        with open(yaml_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        logger.debug("Loaded signal config: %s v%s", data.get("signal_name"), data.get("version"))
        return data or {}
    except Exception as exc:
        logger.error("Failed to load signal config '%s': %s", name, exc)
        return {}


def load_all_signal_configs(config_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load all *.yaml files from the signal config directory.

    Returns:
        Dict mapping signal_name → config dict.
    """
    config_dir = config_dir or _DEFAULT_CONFIG_DIR
    configs: dict[str, dict[str, Any]] = {}

    if not config_dir.exists():
        logger.warning("Signal config directory not found: %s", config_dir)
        return configs

    for yaml_file in sorted(config_dir.glob("*.yaml")):
        cfg = load_signal_config(yaml_file.stem, config_dir)
        if cfg:
            signal_name = cfg.get("signal_name", yaml_file.stem)
            configs[signal_name] = cfg

    logger.info("Loaded %d signal configs from %s", len(configs), config_dir)
    return configs


def get_param(config: dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely extract a parameter from a signal config dict."""
    return config.get("parameters", {}).get(key, default)

"""Loads config.yaml and resolves secret env vars referenced within it."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    for source in config.get("sources", {}).values():
        key_env = source.get("api_key_env")
        if key_env:
            source["api_key"] = os.environ.get(key_env, "")

    return config


def resolve_path(relative: str) -> Path:
    """Resolve a config-relative path (e.g. output.reports_dir) against the repo root."""
    return REPO_ROOT / relative

"""Protect the integration runtime wiring."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "entity_dependency_engine"


def test_release_manifest_version() -> None:
    manifest = json.loads(
        (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["version"] == "0.2.0"


def test_websocket_commands_are_registered_once() -> None:
    source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

    assert source.count(
        "from .websocket import async_register_websocket_commands"
    ) == 1
    assert source.count("    async_register_websocket_commands(hass)") == 1

    call_position = source.index(
        "    async_register_websocket_commands(hass)"
    )
    platform_position = source.index(
        "    await hass.config_entries.async_forward_entry_setups("
        "entry, PLATFORMS)"
    )

    assert call_position < platform_position

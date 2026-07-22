"""Contract tests for the first Home Assistant panel shell."""

from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "entity_dependency_engine"
FRONTEND_PY = INTEGRATION / "frontend.py"
PANEL_JS = INTEGRATION / "frontend" / "entity-dependency-panel.js"


def test_frontend_python_module_parses() -> None:
    ast.parse(FRONTEND_PY.read_text(encoding="utf-8"))


def test_manifest_declares_frontend_dependency_and_alpha_version() -> None:
    manifest = json.loads(
        (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
    )

    assert "frontend" in manifest["dependencies"]
    assert manifest["version"] == "0.2.0-alpha.2"


def test_panel_is_admin_only_and_uses_stable_url() -> None:
    source = FRONTEND_PY.read_text(encoding="utf-8")

    assert 'PANEL_URL_PATH = "entity-dependency-engine"' in source
    assert 'PANEL_COMPONENT_NAME = "entity-dependency-engine-panel"' in source
    assert "require_admin=True" in source
    assert "async_panel_exists" in source
    assert "async_remove_panel" in source


def test_panel_is_wired_into_config_entry_lifecycle() -> None:
    source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

    assert source.count(
        "from .frontend import async_register_frontend, "
        "async_unregister_frontend"
    ) == 1
    assert source.count("    await async_register_frontend(hass)") == 1
    assert source.count("        async_unregister_frontend(hass)") == 1


def test_panel_javascript_has_required_home_assistant_contract() -> None:
    source = PANEL_JS.read_text(encoding="utf-8")

    assert 'customElements.define("entity-dependency-engine-panel"' in source
    assert 'type: "entity_dependency_engine/search_entities"' in source
    assert 'type: "entity_dependency_engine/get_graph"' in source
    assert 'scope: "direct"' in source
    assert 'new CustomEvent("hass-more-info"' in source


def test_panel_uses_home_assistant_theme_variables() -> None:
    source = PANEL_JS.read_text(encoding="utf-8")

    required_variables = {
        "--primary-background-color",
        "--card-background-color",
        "--primary-text-color",
        "--secondary-text-color",
        "--divider-color",
        "--primary-color",
    }

    for variable in required_variables:
        assert f"var({variable}" in source

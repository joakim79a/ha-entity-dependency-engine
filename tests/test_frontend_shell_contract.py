"""Contract tests for the Home Assistant panel shell."""

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
    assert manifest["version"] == "0.2.0-alpha.5"


def test_panel_is_admin_only_and_uses_stable_url() -> None:
    source = FRONTEND_PY.read_text(encoding="utf-8")

    assert 'PANEL_URL_PATH = "entity-dependency-engine"' in source
    assert 'PANEL_COMPONENT_NAME = "entity-dependency-engine"' in source
    assert "require_admin=True" in source
    assert "async_panel_exists" in source
    assert "async_remove_panel" in source
    assert "0.2.0-alpha.5" in source


def test_panel_is_wired_into_config_entry_lifecycle() -> None:
    source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

    assert source.count(
        "from .frontend import async_register_frontend, "
        "async_unregister_frontend"
    ) == 1
    assert source.count("    await async_register_frontend(hass)") == 1
    assert source.count("    async_unregister_frontend(hass)") == 1


def test_panel_javascript_has_required_home_assistant_contract() -> None:
    source = PANEL_JS.read_text(encoding="utf-8")

    assert 'const PANEL_TAG = "ha-panel-entity-dependency-engine";' in source
    assert "customElements.define(PANEL_TAG" in source
    assert 'type: "entity_dependency_engine/search_entities"' in source
    assert 'type: "entity_dependency_engine/get_graph"' in source
    assert 'scope: "direct"' in source
    assert 'new CustomEvent("hass-more-info"' in source


def test_panel_keeps_interactive_elements_stable() -> None:
    source = PANEL_JS.read_text(encoding="utf-8")
    hass_setter = source.split("  set hass(value) {", 1)[1].split(
        "  get hass()", 1
    )[0]

    assert "this._renderShell();" not in hass_setter
    assert 'addEventListener("input"' in source
    assert "window.setTimeout" in source
    assert "this._searchRequestId" in source
    assert "this._graphRequestId" in source


def test_panel_reports_total_results_and_supports_scrolling() -> None:
    source = PANEL_JS.read_text(encoding="utf-8")

    assert "this._entityTotal" in source
    assert "result.total" in source
    assert "Showing ${shown} of ${total}" in source
    assert "overflow-y: auto" in source
    assert "overscroll-behavior: contain" in source
    assert "touch-action: pan-y" in source


def test_panel_supports_node_focus_and_navigation_history() -> None:
    source = PANEL_JS.read_text(encoding="utf-8")

    assert "data-focus-entity" in source
    assert "data-node-id" in source
    assert "this._activeNodeId" in source
    assert "this._navigationHistory" in source
    assert "this._navigationIndex" in source
    assert 'id="history-back"' in source
    assert 'id="history-forward"' in source
    assert "window.history.back()" in source
    assert "window.history.forward()" in source


def test_panel_syncs_selected_entity_with_url() -> None:
    source = PANEL_JS.read_text(encoding="utf-8")

    assert 'const ENTITY_QUERY_PARAMETER = "entity";' in source
    assert "new URL(window.location.href)" in source
    assert "url.searchParams.set" in source
    assert "window.history.pushState" in source
    assert "window.history.replaceState" in source
    assert 'window.addEventListener("popstate"' in source
    assert 'id="direct-link"' in source


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

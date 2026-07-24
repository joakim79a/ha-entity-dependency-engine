"""Contract tests for the Home Assistant panel shell."""

from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "entity_dependency_engine"
FRONTEND_PY = INTEGRATION / "frontend.py"
FRONTEND_ROOT = INTEGRATION / "frontend"
PANEL_JS = FRONTEND_ROOT / "entity-dependency-panel.js"
LAYOUT_JS = FRONTEND_ROOT / "entity-dependency-layout.js"


def test_frontend_python_module_parses() -> None:
    ast.parse(FRONTEND_PY.read_text(encoding="utf-8"))


def test_manifest_declares_frontend_dependency_and_alpha_version() -> None:
    manifest = json.loads(
        (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
    )

    assert "frontend" in manifest["dependencies"]
    assert manifest["version"] == "0.2.0-rc.1"


def test_panel_is_admin_only_and_uses_stable_url() -> None:
    source = FRONTEND_PY.read_text(encoding="utf-8")

    assert 'PANEL_URL_PATH = "entity-dependency-engine"' in source
    assert 'PANEL_COMPONENT_NAME = "entity-dependency-engine"' in source
    assert "require_admin=True" in source
    assert "async_panel_exists" in source
    assert "async_remove_panel" in source
    assert "0.2.0-rc.1" in source


def test_panel_is_wired_into_config_entry_lifecycle() -> None:
    source = (
        INTEGRATION / "__init__.py"
    ).read_text(encoding="utf-8")

    assert source.count(
        "from .frontend import async_register_frontend, "
        "async_unregister_frontend"
    ) == 1
    assert source.count("    await async_register_frontend(hass)") == 1
    assert source.count("    async_unregister_frontend(hass)") == 1


def test_panel_javascript_has_required_home_assistant_contract() -> None:
    source = PANEL_JS.read_text(encoding="utf-8")

    assert (
        'const PANEL_TAG = "ha-panel-entity-dependency-engine";'
        in source
    )
    assert "customElements.define(" in source
    assert 'type: "entity_dependency_engine/search_entities"' in source
    assert 'type: "entity_dependency_engine/get_graph"' in source
    assert 'type: "entity_dependency_engine/expand_node"' in source
    assert 'new CustomEvent("hass-more-info"' in source


def test_panel_uses_separate_layered_layout_module() -> None:
    panel_source = PANEL_JS.read_text(encoding="utf-8")
    layout_source = LAYOUT_JS.read_text(encoding="utf-8")

    assert 'from "./entity-dependency-layout.js?v=0.2.0-rc.1"' in (
        panel_source
    )
    assert "export const buildLayeredLayout" in layout_source
    assert "export const createEdgePath" in layout_source


def test_panel_keeps_interactive_elements_stable() -> None:
    source = PANEL_JS.read_text(encoding="utf-8")
    hass_setter = source.split("  set hass(value) {", 1)[1].split(
        "  get hass()",
        1,
    )[0]

    assert "this._renderShell();" not in hass_setter
    assert 'addEventListener("input"' in source
    assert "window.setTimeout" in source
    assert "this._searchRequestId" in source
    assert "this._graphRequestId" in source


def test_panel_retains_expansion_and_navigation_controls() -> None:
    source = PANEL_JS.read_text(encoding="utf-8")

    assert "data-expand-parents" in source
    assert "data-expand-children" in source
    assert "data-focus-entity" in source
    assert 'id="history-back"' in source
    assert 'id="history-forward"' in source
    assert 'id="reset-view"' in source
    assert 'id="center-root"' in source
    assert 'id="direct-link"' in source


def test_panel_supports_two_dimensional_scrolling() -> None:
    source = PANEL_JS.read_text(encoding="utf-8")

    assert "overflow-x: auto" in source
    assert "overflow-y: auto" in source
    assert "scrollbar-gutter: stable both-edges" in source
    assert "this._centerRoot(" in source


def test_root_and_selected_node_have_distinct_visual_styles() -> None:
    source = PANEL_JS.read_text(encoding="utf-8")

    assert ".node-card.root-focus" in source
    assert "border: 4px solid var(--primary-color)" in source
    assert ".node-card.active:not(.root-focus)" in source
    assert "CENTRUM" in source


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

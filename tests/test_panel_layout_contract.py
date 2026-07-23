"""Static contract tests for the vertical graph layout."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYOUT_JS = (
    ROOT
    / "custom_components"
    / "entity_dependency_engine"
    / "frontend"
    / "entity-dependency-layout.js"
)


def test_layout_assigns_signed_vertical_levels() -> None:
    source = LAYOUT_JS.read_text(encoding="utf-8")

    assert "return -upstreamDistance" in source
    assert "return downstreamDistance" in source
    assert "node.id === rootId" in source
    assert "? 0" in source


def test_layout_is_cycle_safe_and_deterministic() -> None:
    source = LAYOUT_JS.read_text(encoding="utf-8")

    assert "distances.has(next)" in source
    assert "breadthFirstDistances" in source
    assert "stableLabel" in source
    assert "optimizeLayerOrder" in source


def test_layout_centres_each_layer_horizontally() -> None:
    source = LAYOUT_JS.read_text(encoding="utf-8")

    assert "const startX = (canvasWidth - width) / 2" in source
    assert "horizontalGap" in source
    assert "verticalGap" in source
    assert "canvasHeight" in source


def test_layout_creates_directional_edge_paths() -> None:
    source = LAYOUT_JS.read_text(encoding="utf-8")

    assert "export const createEdgePath" in source
    assert "sourceCenterY <= targetCenterY" in source
    assert "`C ${startX} ${middleY}," in source

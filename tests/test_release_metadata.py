"""Validate release-candidate metadata and documentation."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "entity_dependency_engine"
VERSION = "0.2.0-rc.1"


def test_release_versions_are_consistent() -> None:
    manifest = json.loads(
        (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == VERSION

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.2.0rc1"' in pyproject

    frontend_python = (INTEGRATION / "frontend.py").read_text(
        encoding="utf-8"
    )
    panel_path = (
        INTEGRATION
        / "frontend"
        / "entity-dependency-panel.js"
    )
    layout_path = (
        INTEGRATION
        / "frontend"
        / "entity-dependency-layout.js"
    )

    panel = panel_path.read_text(encoding="utf-8")
    layout = layout_path.read_text(encoding="utf-8")

    assert VERSION in frontend_python
    assert VERSION in panel
    assert "0.2.0 RC 1" in panel

    assert (
        'from "./entity-dependency-layout.js?v=0.2.0-rc.1"'
        in panel
    )
    assert "export const buildLayeredLayout" in layout
    assert "export const createEdgePath" in layout


def test_required_release_documents_exist() -> None:
    required = [
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "RELEASE_STATUS.md",
        "docs/UPGRADING.md",
        "docs/RELEASE_CHECKLIST.md",
        "docs/SCREENSHOTS.md",
        "docs/RELEASE_NOTES_0.2.0-rc.1.md",
        ".github/pull_request_template.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
    ]

    for relative in required:
        assert (ROOT / relative).is_file(), relative


def test_release_screenshots_exist() -> None:
    required = [
        "docs/images/panel-overview.jpg",
        "docs/images/panel-expanded-tree.jpg",
        "docs/images/panel-search.jpg",
    ]

    for relative in required:
        path = ROOT / relative
        assert path.is_file(), f"Missing screenshot: {relative}"
        assert path.stat().st_size > 10_000, (
            f"Screenshot too small: {relative}"
        )


def test_readme_documents_compatibility() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "v0.2.0-rc.1" in readme
    assert "entity_dependency_engine.generate_report" in readme
    assert "sensor.entity_dependency_engine_last_report" in readme
    assert "docs/images/panel-overview.jpg" in readme
    assert "docs/images/panel-expanded-tree.jpg" in readme
    assert "docs/images/panel-search.jpg" in readme


def test_runtime_files_do_not_reference_alpha_7() -> None:
    suffixes = {".py", ".js", ".json", ".md", ".yaml", ".yml"}

    for path in INTEGRATION.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue

        source = path.read_text(encoding="utf-8")

        assert "0.2.0-alpha.7" not in source, path
        assert "0.2.0 alpha.7" not in source, path

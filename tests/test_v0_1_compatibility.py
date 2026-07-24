"""Regression guards for the public v0.1.0 compatibility contract."""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

from engine.application import generate_report
from tests.test_generate_report import _create_config_dir


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT / "custom_components" / "entity_dependency_engine"


def _literal_assignments(path: Path) -> dict[str, object]:
    """Return simple module-level literal assignments without importing HA."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assignments: dict[str, object] = {}

    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue

        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue

        try:
            assignments[target.id] = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue

    return assignments


def test_v0_1_action_constants_and_defaults_are_stable() -> None:
    """Protect the action name, fields, defaults, and supported languages."""
    values = _literal_assignments(INTEGRATION_DIR / "const.py")

    assert values["DOMAIN"] == "entity_dependency_engine"
    assert values["SERVICE_GENERATE_REPORT"] == "generate_report"

    assert values["ATTR_ENTITY_ID"] == "entity_id"
    assert values["ATTR_INCLUDE_STRUCTURAL"] == "include_structural"
    assert values["ATTR_LANGUAGE"] == "language"
    assert values["ATTR_MAX_DEPTH"] == "max_depth"
    assert values["ATTR_SAVE_PUBLIC_COPY"] == "save_public_copy"

    assert values["DEFAULT_INCLUDE_STRUCTURAL"] is False
    assert values["DEFAULT_SAVE_PUBLIC_COPY"] is False
    assert values["SUPPORTED_LANGUAGES"] == {"en", "sv"}


def test_v0_1_service_description_fields_are_stable() -> None:
    """Protect the fields exposed by Home Assistant's action UI."""
    services = yaml.safe_load(
        (INTEGRATION_DIR / "services.yaml").read_text(encoding="utf-8")
    )

    fields = services["generate_report"]["fields"]

    assert {
        "entity_id",
        "include_structural",
        "max_depth",
        "language",
        "save_public_copy",
    }.issubset(fields)

    assert fields["entity_id"]["required"] is True
    assert fields["include_structural"]["default"] is False
    assert fields["save_public_copy"]["default"] is False
    assert fields["language"]["selector"]["select"]["options"] == ["en", "sv"]


def test_v0_1_sensor_identity_and_recorder_protection_are_stable() -> None:
    """Protect the entity identity and large report recorder exclusion."""
    source = (INTEGRATION_DIR / "sensor.py").read_text(encoding="utf-8")

    assert '_attr_unique_id = "last_report"' in source
    assert 'return "entity_dependency_engine_last_report"' in source
    assert '_attr_should_poll = False' in source
    assert '_unrecorded_attributes = frozenset({"report"})' in source


def test_v0_1_private_report_response_contract(tmp_path: Path) -> None:
    """Protect private storage, English output, and response keys."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    _create_config_dir(config_dir)

    private_dir = tmp_path / "private"

    result = generate_report(
        config_dir=config_dir,
        entity_id="sensor.pulse_elpris",
        private_output_dir=private_dir,
        language="en",
        include_structural=False,
        public_output_dir=None,
    )
    response = result.as_response(include_report_text=True)

    required_keys = {
        "ok",
        "entity_id",
        "summary",
        "parents",
        "children",
        "ancestors",
        "descendants",
        "broken",
        "build_warnings",
        "generated",
        "private_file",
        "private_debug_file",
        "private_latest_file",
        "report",
    }

    assert required_keys.issubset(response)
    assert response["ok"] is True
    assert response["entity_id"] == "sensor.pulse_elpris"
    assert "Direct children" in response["report"]

    assert result.private_file == private_dir / "sensor_pulse_elpris.txt"
    assert result.private_debug_file == private_dir / "sensor_pulse_elpris_debug.txt"
    assert result.private_latest_file == private_dir / "latest_report.txt"

    assert result.private_file.exists()
    assert result.private_debug_file.exists()
    assert result.private_latest_file.exists()

    assert "url" not in response
    assert "debug_url" not in response
    assert "latest_url" not in response


def test_v0_1_public_report_response_contract(tmp_path: Path) -> None:
    """Protect optional public storage, Swedish output, and public URLs."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    _create_config_dir(config_dir)

    private_dir = tmp_path / "private"
    public_dir = tmp_path / "public"

    result = generate_report(
        config_dir=config_dir,
        entity_id="sensor.pulse_elpris",
        private_output_dir=private_dir,
        public_output_dir=public_dir,
        language="sv-SE",
        include_structural=False,
    )
    response = result.as_response(include_report_text=True)

    assert "Direkta barn" in response["report"]
    assert response["url"] == (
        "/local/entity_dependency_engine/sensor_pulse_elpris.txt"
    )
    assert response["debug_url"] == (
        "/local/entity_dependency_engine/sensor_pulse_elpris_debug.txt"
    )
    assert response["latest_url"] == (
        "/local/entity_dependency_engine/latest_report.txt"
    )

    assert (public_dir / "sensor_pulse_elpris.txt").exists()
    assert (public_dir / "sensor_pulse_elpris_debug.txt").exists()
    assert (public_dir / "latest_report.txt").exists()
